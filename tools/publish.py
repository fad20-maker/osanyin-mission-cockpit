#!/usr/bin/env python3
"""Publish site/data.enc.json to GitHub through the REST API.

Usage: GH_TOKEN_FILE=<secrets.json> python3 tools/publish.py [message]  (or GH_TOKEN=...)
Reads the repository from GH_REPO (default fad20-maker/osanyin-mission-cockpit).
"""
import base64, json, os, sys, urllib.request, urllib.error

REPO = os.environ.get("GH_REPO", "fad20-maker/osanyin-mission-cockpit")
PATH = "site/data.enc.json"
def _token():
    f = os.environ.get("GH_TOKEN_FILE")
    if f:
        d = json.load(open(f, encoding="utf-8"))
        return d.get("githubToken") or d.get("data", {}).get("githubToken")
    return os.environ["GH_TOKEN"]


TOKEN = _token()
MSG = sys.argv[1] if len(sys.argv) > 1 else "Mise à jour des données"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
API = f"https://api.github.com/repos/{REPO}/contents/{PATH}"
HDR = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
       "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "coordination-osanyin",
       "Content-Type": "application/json"}


def call(method, url, body=None):
    req = urllib.request.Request(url, method=method, headers=HDR, data=json.dumps(body).encode() if body else None)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def main():
    content = open(os.path.join(ROOT, PATH), "rb").read()
    try:
        sha = call("GET", API + "?ref=main")["sha"]
    except urllib.error.HTTPError as e:
        if e.code != 404:
            sys.exit(f"lecture impossible ({e.code})")
        sha = None
    body = {"message": MSG, "branch": "main", "content": base64.b64encode(content).decode(),
            "committer": {"name": "Coordination Osanyin", "email": "fad20-maker@users.noreply.github.com"}}
    if sha:
        body["sha"] = sha
    try:
        res = call("PUT", API, body)
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode()).get("message", "")
        except Exception:
            detail = ""
        sys.exit(f"publication refusée ({e.code}) {detail}")
    print("publié", res["commit"]["sha"][:7])


if __name__ == "__main__":
    main()
