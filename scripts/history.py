import argparse
import csv
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from pathlib import Path
import random


def generate(out: Path, days=56, seed=20261020, end="2026-10-20", courses=12, students=120):
    if not 1 <= days <= 366 or not 3 <= courses <= 100 or not 6 <= students <= 2000:
        raise ValueError("Escala fuera de rango")

    finish = datetime.combine(date.fromisoformat(end), time(), tzinfo=timezone.utc)
    start = finish - timedelta(days=days)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    incidents = []
    for offset in sorted(set([max(0, days // 3), max(0, days - 8)])):
        when = start + timedelta(days=offset, hours=22)
        incidents.append({
            "id": f"INC-{len(incidents) + 1:03d}", "source": "synthetic",
            "start": when.isoformat(), "end": (when + timedelta(minutes=45)).isoformat(),
            "reported_at": (when + timedelta(minutes=12)).isoformat(),
            "reporter": "Docente simulado", "channel": "Mesa de ayuda",
            "description": "El campus tarda en abrir y algunas solicitudes fallan durante las entregas.",
        })
    count = errors = 0
    with (out / "http.jsonl").open("w") as http, (out / "metrics.csv").open("w", newline="") as metrics:
        writer = csv.DictWriter(metrics, fieldnames=[
            "source", "timestamp", "interval_minutes", "requests", "errors_5xx",
            "p95_seconds", "cpu_percent", "memory_mib", "storage_mib", "cron_last_success",
        ])
        writer.writeheader()
        when = start
        storage = 4096.0
        cron_last = start - timedelta(minutes=1)
        while when < finish:
            busy = 12 <= when.hour <= 23 and when.weekday() < 5
            peak = any(datetime.fromisoformat(i["start"]) <= when < datetime.fromisoformat(i["end"]) for i in incidents)
            requests = rng.randint(6, 16) if busy else rng.randint(0, 3)
            requests = requests * 6 if peak else requests
            latencies = []
            bucket_errors = 0
            for n in range(requests):
                status = 503 if peak and rng.random() < .16 else 200
                seconds = round(rng.uniform(3, 12) if peak else rng.uniform(.08, 1.1), 3)
                latency = seconds
                latencies.append(latency)
                bucket_errors += status >= 500
                event = {
                    "source": "synthetic", "timestamp": (when + timedelta(seconds=rng.randrange(900))).isoformat(),
                    "client_ip": f"192.0.2.{rng.randint(1, 200)}", "method": "GET",
                    "path": rng.choice(["/my/", "/course/view.php", "/mod/page/view.php", "/mod/assign/view.php"]),
                    "course_code": f"TUARI-{rng.randint(1, courses):02d}",
                    "actor": f"estudiante{rng.randint(1, students):03d}",
                    "status": status, "request_seconds": seconds, "bytes": rng.randint(2000, 50000),
                }
                http.write(json.dumps(event, ensure_ascii=False) + "\n")
            storage += rng.uniform(.03, .18) * (3 if busy else 1)

            cron_stopped = finish - timedelta(days=2) + timedelta(hours=12) <= when < finish - timedelta(days=2) + timedelta(hours=18)
            if not cron_stopped:
                cron_last = when - timedelta(minutes=1)
            ordered = sorted(latencies)
            p95 = ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)] if ordered else 0
            writer.writerow({
                "source": "synthetic", "timestamp": when.isoformat(), "interval_minutes": 15,
                "requests": requests, "errors_5xx": bucket_errors, "p95_seconds": p95,
                "cpu_percent": round(rng.uniform(85, 99) if peak else rng.uniform(15, 55) if busy else rng.uniform(2, 12), 1),
                "memory_mib": round(rng.uniform(850, 1100) if peak else rng.uniform(300, 650), 1),
                "storage_mib": round(storage, 2), "cron_last_success": cron_last.isoformat(),
            })
            count += requests
            errors += bucket_errors
            when += timedelta(minutes=15)
    (out / "tickets.json").write_text(json.dumps(incidents, indent=2, ensure_ascii=False) + "\n")
    manifest = {
        "dataset_version": 1, "source": "synthetic", "seed": seed, "days": days,
        "start_inclusive": start.isoformat(), "end_exclusive": finish.isoformat(),
        "timezone": "UTC", "courses": courses, "students": students,
        "http_events": count, "errors_5xx": errors,
        "note": "Caso didáctico inventado. Métricas correlacionadas por diseño; no demuestran causalidad. No son mediciones del host ni eventos históricos de la BD Moodle.",
        "sha256": {name: hashlib.sha256((out / name).read_bytes()).hexdigest()
                   for name in ["http.jsonl", "metrics.csv", "tickets.json"]},
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generar el historial sintético del laboratorio.")
    parser.add_argument("--out", type=Path, default=Path("evidence/history"))
    parser.add_argument("--days", type=int, default=56)
    parser.add_argument("--seed", type=int, default=20261020)
    parser.add_argument("--end", default="2026-10-20")
    parser.add_argument("--courses", type=int, default=12)
    parser.add_argument("--students", type=int, default=120)
    args = parser.parse_args()
    print(json.dumps(generate(args.out, args.days, args.seed, args.end, args.courses, args.students), indent=2))
