#!/usr/bin/env python3
"""Export the team-visible part of the mission cockpit and encrypt it for the web viewer.

Usage: python3 tools/export.py <snapshot_dir> <access_code> [site_dir]

<snapshot_dir> contains one sub-folder per collection (tasks, points, meetings,
journal, inbox, meta), each holding <doc_id>.json files.
Journal and inbox are never exported: they stay in the coordination console.
"""
import base64, hashlib, json, os, re, sys, datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ITER = 210_000
PRIVATE_FIELDS = {"gcalEventId", "gcalSig", "inboxId"}


def load(snap, coll):
    d = os.path.join(snap, coll)
    out = []
    if not os.path.isdir(d):
        return out
    for f in sorted(os.listdir(d)):
        if f.endswith(".json"):
            doc = json.load(open(os.path.join(d, f), encoding="utf-8"))
            doc = {k: v for k, v in doc.items() if k not in PRIVATE_FIELDS}
            doc["id"] = f[:-5]
            out.append(doc)
    return out


def meta(snap, name):
    p = os.path.join(snap, "meta", name + ".json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


TECH_ALERT = re.compile(
    r"vitrine|web viewer|incompl|actualisation|refresh|google agenda|agenda google|google calendar|"
    r"synchronis|github|dossier local|local folder|ordinateur|computer|code d'acc|access code",
    re.IGNORECASE)


def team_state(state):
    """Technical alerts stay in the coordination console; the team only sees mission alerts."""
    if not state:
        return state
    state = dict(state)
    state["alerts"] = [a for a in (state.get("alerts") or [])
                       if not a.get("tech") and not TECH_ALERT.search((a.get("text") or "") + " " + (a.get("en") or ""))]
    return state


def contributed(docs, key):
    for d in docs:
        if (d.get("author") or "").lower().startswith(key) and d.get("kind") in ("rapport", "cr") and (d.get("date") or "") >= "2026-10-16":
            return True
    return False


def main():
    snap, code = sys.argv[1], sys.argv[2]
    site = sys.argv[3] if len(sys.argv) > 3 else os.path.join(os.path.dirname(__file__), "..", "site")
    private = load(snap, "journal") + load(snap, "inbox")
    data = {
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tasks": load(snap, "tasks"),
        "points": load(snap, "points"),
        "meetings": load(snap, "meetings"),
        "state": team_state(meta(snap, "state")),
        "programme": meta(snap, "programme"),
        "reperes": meta(snap, "reperes"),
        "bilan": meta(snap, "bilan"),
        "contrib": {"Petri": contributed(private, "petri"), "Baba Guissé": contributed(private, "baba")},
    }
    plain = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    stamp = hashlib.sha256(plain).hexdigest()[:16]
    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(code.strip().upper().encode("utf-8"))
    ct = AESGCM(key).encrypt(iv, plain, None)
    pack = {"v": 1, "stamp": stamp, "iter": ITER,
            "salt": base64.b64encode(salt).decode(), "iv": base64.b64encode(iv).decode(), "ct": base64.b64encode(ct).decode()}
    out = os.path.join(site, "data.enc.json")
    json.dump(pack, open(out, "w"), separators=(",", ":"))
    print("written", out, stamp, len(plain), "bytes")


if __name__ == "__main__":
    main()
