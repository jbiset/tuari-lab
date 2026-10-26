import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

from history import generate

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ["docker", "compose", "--env-file", str(ROOT / ".env")]


def run(args, **kwargs):
    kwargs.setdefault("check", True)
    return subprocess.run(args, cwd=ROOT, **kwargs)


def compose(*args, **kwargs):
    return run(COMPOSE + list(args), **kwargs)


def settings():
    path = ROOT / ".env"
    if not path.exists():
        raise ValueError("Primero ejecutar ./lab setup")

    result = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip().strip("\"'")
    return {key: os.environ.get(key, value) for key, value in result.items()}


def now():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def history(config):
    manifest = generate(ROOT / "evidence/history", int(config.get("HISTORY_DAYS", 56)),
                        int(config.get("DATASET_SEED", 20261020)), courses=int(config.get("COURSE_COUNT", 12)),
                        students=int(config.get("STUDENT_COUNT", 120)))
    print(f'Historial sintético: {manifest["http_events"]} eventos en evidence/history')


def query():
    with (ROOT / "sql/relevamiento.sql").open("rb") as source:
        compose("exec", "-T", "db", "sh", "-c",
                "MYSQL_PWD='TuariLectura-2026!' exec mariadb --user=relevador --table moodle", stdin=source)


def verify():
    compose("exec", "-T", "--user", "www-data", "moodle", "php", "/opt/tuari/verify.php")

    denied = compose("exec", "-T", "db", "sh", "-c",
                     "MYSQL_PWD='TuariLectura-2026!' mariadb --user=relevador moodle -e 'DELETE FROM mdl_user WHERE 1=0'",
                     check=False, capture_output=True, text=True)
    if denied.returncode == 0 or "1142" not in denied.stderr:
        raise ValueError("No se verificó la denegación de escritura del usuario de lectura")
    print("Identidad SQL de relevamiento: escritura denegada (1142).")


def backup():
    out = ROOT / "backups" / now()
    out.mkdir(parents=True)

    compose("stop", "simulator", "proxy", "cron", "moodle")
    try:
        with (out / "database.sql").open("wb") as destination:
            compose("exec", "-T", "db", "sh", "-c",
                    'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" exec mariadb-dump --user=root --single-transaction --routines --databases moodle --add-drop-database',
                    stdout=destination)
        with (out / "moodledata.tar.gz").open("wb") as destination:
            compose("run", "--rm", "--no-deps", "-T", "--entrypoint", "tar", "init",
                    "-czf", "-", "-C", "/var/moodledata", ".", stdout=destination)
        images = compose("images", "--format", "json", capture_output=True, text=True).stdout
        keys = ["STUDENT_COUNT", "COURSE_COUNT", "TEACHER_COUNT", "HISTORY_DAYS", "DATASET_SEED", "MOODLE_URL"]
        config = settings()
        manifest = {"format": 1, "dataset_version": 1, "created_at": now(), "images": images,
                    "settings": {key: config.get(key) for key in keys},
                    "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in [out / "database.sql", out / "moodledata.tar.gz"]}}
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    finally:
        compose("start", "moodle", "cron", "proxy")
    print(f"Respaldo consistente: {out.relative_to(ROOT)}")


def validate_backup(out):
    manifest = json.loads((out / "manifest.json").read_text())
    if manifest.get("format") != 1 or set(manifest.get("sha256", {})) != {"database.sql", "moodledata.tar.gz"}:
        raise ValueError("Formato de respaldo no reconocido")
    for name, digest in manifest["sha256"].items():
        if hashlib.sha256((out / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Checksum incorrecto: {name}")
    with tarfile.open(out / "moodledata.tar.gz", "r:gz") as archive:
        for member in archive:
            if member.name.startswith("/") or ".." in Path(member.name).parts or member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                raise ValueError("Archivo de respaldo con entrada no permitida")
    return manifest


def restore(out):
    manifest = validate_backup(out)
    config = settings()
    for key in ["STUDENT_COUNT", "COURSE_COUNT", "TEACHER_COUNT"]:
        if str(manifest["settings"][key]) != str(config.get(key)):
            raise ValueError(f"Ajustar {key} en .env a la escala del respaldo antes de restaurar")
    compose("stop", "simulator", "proxy", "cron", "moodle")

    with (out / "database.sql").open("rb") as source:
        compose("exec", "-T", "db", "sh", "-c", 'MYSQL_PWD="$MARIADB_ROOT_PASSWORD" exec mariadb --user=root', stdin=source)
    with (out / "moodledata.tar.gz").open("rb") as source:
        compose("run", "--rm", "--no-deps", "-T", "--entrypoint", "sh", "init", "-c",
                'find /var/moodledata -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + && tar -xzf - -C /var/moodledata', stdin=source)
    compose("run", "--rm", "--no-deps", "-T", "--user", "www-data", "--entrypoint", "php", "init", "admin/cli/purge_caches.php")
    compose("start", "moodle", "cron", "proxy")
    verify()
    print("Restauración completada. Ejecutar ./lab smoke para comprobar acceso web y sesiones.")


def simulate(users=4, rounds=5, delay=1):
    catalog = compose("exec", "-T", "--user", "www-data", "moodle", "php", "/opt/tuari/catalog.php", capture_output=True, text=True).stdout.strip()
    json.loads(catalog)
    compose("--profile", "activity", "run", "--rm", "--no-deps", "-T",
            "-e", f"SIM_USERS={users}", "-e", f"SIM_ROUNDS={rounds}", "-e", f"SIM_DELAY={delay}",
            "-e", f"SIM_CATALOG={catalog}", "simulator")


def export_evidence():
    out = ROOT / "evidence/live" / now()
    out.mkdir(parents=True)
    for filename, args in [
        ("services.txt", ["ps", "-a"]),
        ("images.json", ["images", "--format", "json"]),
        ("logs.txt", ["logs", "--no-color", "--timestamps", "--tail", "5000", "proxy", "moodle", "cron", "db"]),
        ("resources.json", ["stats", "--no-stream", "--format", "json"]),
    ]:
        with (out / filename).open("w") as destination:
            compose(*args, stdout=destination)
    with (out / "queries.txt").open("w") as destination, (ROOT / "sql/relevamiento.sql").open("rb") as source:
        compose("exec", "-T", "db", "sh", "-c",
                "MYSQL_PWD='TuariLectura-2026!' exec mariadb --user=relevador --table moodle", stdin=source, stdout=destination)
    print(f"Evidencias reales (recorte de hasta 5000 líneas por servicio): {out.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser(description="Administrar el laboratorio TUARI.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ["setup", "up", "down", "status", "history", "query", "verify", "smoke", "backup", "evidence", "check"]:
        commands.add_parser(name)
    logs = commands.add_parser("logs")
    logs.add_argument("service", nargs="?", default="proxy", choices=["proxy", "moodle", "cron", "db", "init", "mail"])
    sim = commands.add_parser("simulate")
    sim.add_argument("--users", type=int, default=4)
    sim.add_argument("--rounds", type=int, default=5)
    sim.add_argument("--delay", type=float, default=1)
    scenario = commands.add_parser("scenario")
    scenario.add_argument("state", choices=["cron-stopped", "normal"])
    restore_parser = commands.add_parser("restore")
    restore_parser.add_argument("directory", type=Path)
    restore_parser.add_argument("--confirm", action="store_true", required=True, help="Reemplaza la base y moodledata del proyecto actual")
    reset = commands.add_parser("reset")
    reset.add_argument("--confirm", action="store_true", required=True, help="Elimina los volúmenes del proyecto actual")
    args = parser.parse_args()
    if args.command == "setup":
        if not (ROOT / ".env").exists():
            shutil.copyfile(ROOT / ".env.example", ROOT / ".env")
            os.chmod(ROOT / ".env", 0o600)
        history(settings())
        print("Configuración lista. Revisar .env y ejecutar ./lab up")
        return
    if args.command == "check":
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
        compose_config = ["docker", "compose", "--env-file", str(ROOT / ".env.example"), "config", "--quiet"]
        run(compose_config)
        for path in sorted((ROOT / "docker/moodle").rglob("*.php")):
            run(["php", "-n", "-l", str(path)])
        for path in list((ROOT / "docker").rglob("*.sh")) + [ROOT / "lab"]:
            run(["sh", "-n", str(path)])
        return
    config = settings()
    if args.command == "history":
        history(config)
    elif args.command == "up":
        compose("config", "--quiet")
        compose("up", "-d", "--build", "--wait", "--wait-timeout", "600")
        print(f'Campus: {config["MOODLE_URL"]}; correo: http://localhost:{config.get("MAIL_PORT", "8025")}')
    elif args.command == "down":
        compose("--profile", "activity", "down")
    elif args.command == "status":
        compose("ps", "-a")
    elif args.command == "logs":
        compose("logs", "--tail", "100", "-f", args.service)
    elif args.command == "query":
        query()
    elif args.command == "verify":
        verify()
    elif args.command == "simulate":
        simulate(args.users, args.rounds, args.delay)
    elif args.command == "smoke":
        verify()
        simulate(3, 8, .1)
    elif args.command == "scenario":
        compose("stop" if args.state == "cron-stopped" else "start", "cron")
        print("Cron detenido." if args.state == "cron-stopped" else "Cron reactivado; revisar logs y correo.")
    elif args.command == "backup":
        backup()
    elif args.command == "restore":
        restore(args.directory.resolve())
    elif args.command == "evidence":
        export_evidence()
    elif args.command == "reset":
        compose("--profile", "activity", "down", "--volumes", "--remove-orphans")
        print("Volúmenes eliminados. ./lab up creará nuevamente el campus. Backups e historial se conservan.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
