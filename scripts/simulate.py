from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from http.cookiejar import CookieJar
import json
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request


class CampusHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.token = None
        self.links = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "input" and attrs.get("name") == "logintoken":
            self.token = attrs.get("value")
        if tag == "a" and attrs.get("href"):
            self.links.add(attrs["href"])


class InternalRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, target, public):
        self.target = target.rstrip("/")
        self.allowed = {urllib.parse.urlsplit(target).netloc, urllib.parse.urlsplit(public).netloc}

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        if parsed.netloc and parsed.netloc not in self.allowed:
            raise ValueError("Redirección fuera del laboratorio")
        internal = self.target + parsed.path + ("?" + parsed.query if parsed.query else "")
        return super().redirect_request(req, fp, code, msg, headers, internal)


class CampusClient:
    def __init__(self, target, public):
        self.target = target.rstrip("/")
        self.allowed = {urllib.parse.urlsplit(target).netloc, urllib.parse.urlsplit(public).netloc}
        self.opener = urllib.request.build_opener(InternalRedirect(target, public), urllib.request.HTTPCookieProcessor(CookieJar()))
        self.opener.addheaders = [("User-Agent", "TUARI-Lab-Simulator/1.0")]

    def request(self, path, data=None):
        parsed = urllib.parse.urlsplit(path)
        if parsed.netloc and parsed.netloc not in self.allowed:
            raise ValueError("URL fuera del laboratorio")
        url = self.target + parsed.path + ("?" + parsed.query if parsed.query else "")
        payload = urllib.parse.urlencode(data).encode() if data else None
        started = time.monotonic()
        with self.opener.open(url, payload, timeout=45) as response:
            body = response.read().decode("utf-8", errors="replace")
            final_path = urllib.parse.urlsplit(response.url).path
        parser = CampusHTML()
        parser.feed(body)
        return body, parser, final_path, round(time.monotonic() - started, 3)

    def login(self, username, password):
        _, parsed, _, _ = self.request("/login/index.php")
        if not parsed.token:
            raise RuntimeError("Moodle no entregó logintoken")
        self.request("/login/index.php", {"username": username, "password": password, "logintoken": parsed.token})
        body, parsed, path, elapsed = self.request("/my/")
        if path.startswith("/login/") or "/login/logout.php" not in body:
            raise RuntimeError("La sesión no quedó autenticada")
        return parsed


def worker(index, config):
    rng = random.Random(index)
    username = f"estudiante{index:03d}"
    client = CampusClient(config["target"], config["public"])
    parsed = client.login(username, config["password"])
    paths = {"/my/", "/course/index.php"}
    for course in config.get("catalog", []):
        if course["institution"] == (index - 1) % 3:
            paths.add(f'/course/view.php?id={int(course["id"])}')
    paths.update(link for link in parsed.links if urllib.parse.urlsplit(link).path == "/course/view.php")
    completed = 0
    for _ in range(config["rounds"]):
        path = rng.choice(sorted(paths))
        _, parsed, final, elapsed = client.request(path)
        if final.startswith("/login/"):
            raise RuntimeError("Sesión perdida")
        for link in parsed.links:
            url = urllib.parse.urlsplit(link)
            if url.path in ["/course/view.php", "/mod/page/view.php", "/mod/forum/view.php", "/mod/assign/view.php"]:
                if not url.netloc or url.netloc in client.allowed:
                    paths.add(link)
        print(json.dumps({"source": "live-simulator", "timestamp": datetime.now(timezone.utc).isoformat(),
                          "user": username, "path": final, "elapsed_seconds": elapsed}), flush=True)
        completed += 1
        time.sleep(config["delay"])
    return completed


def main():
    students = int(os.getenv("STUDENT_COUNT", "120"))
    users = int(os.getenv("SIM_USERS", "4"))
    config = {"target": os.getenv("TARGET_URL", "http://proxy"),
              "public": os.getenv("PUBLIC_URL", "http://localhost:8080"),
              "password": os.environ["PARTICIPANT_PASSWORD"],
              "rounds": int(os.getenv("SIM_ROUNDS", "5")), "delay": float(os.getenv("SIM_DELAY", "1")),
              "catalog": json.loads(os.getenv("SIM_CATALOG", "[]"))}
    if not 1 <= users <= min(students, 50) or not 1 <= config["rounds"] <= 1000 or config["delay"] < 0:
        raise ValueError("SIM_USERS=1..50 (y <= estudiantes), SIM_ROUNDS=1..1000, SIM_DELAY>=0")
    with ThreadPoolExecutor(max_workers=users) as pool:
        total = sum(pool.map(lambda n: worker(n, config), range(1, users + 1)))
    print(json.dumps({"result": "ok", "authenticated_users": users, "completed_requests": total}))


if __name__ == "__main__":
    main()
