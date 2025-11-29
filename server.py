from flask import Flask, request, jsonify
import json
import os

# Always resolve keys.json relative to this file so it works on Render, too.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_FILE = os.path.join(BASE_DIR, "keys.json")

app = Flask(__name__)


def load_db():
    if not os.path.isfile(DATABASE_FILE):
        print("[SERVER] keys.json not found at:", DATABASE_FILE)
        return []
    with open(DATABASE_FILE, "r") as f:
        db = json.load(f)
    print(f"[SERVER] Loaded DB with {len(db)} entries")
    return db


def save_db(db):
    with open(DATABASE_FILE, "w") as f:
        json.dump(db, f, indent=4)
    print("[SERVER] DB saved to keys.json")


def _norm(k: str) -> str:
    """Normalize a license key: remove hyphens and uppercase."""
    if not isinstance(k, str):
        return ""
    return k.replace("-", "").upper()


@app.route("/validate", methods=["POST"])
def validate():
    data = request.json or {}
    key = data.get("key")
    hwid = data.get("hwid")

    print("\n========== /validate called ==========")
    print("[SERVER] Raw client key:", repr(key))
    print("[SERVER] Raw client HWID:", repr(hwid))

    if not key or not hwid:
        print("[SERVER] Missing key or HWID")
        return jsonify({"status": "error", "msg": "Missing key or hwid"}), 400

    db = load_db()
    if not db:
        print("[SERVER] WARNING: DB empty, no keys to compare.")
        return jsonify({"status": "denied", "msg": "Invalid key"})

    norm_client_key = _norm(key)
    print("[SERVER] Normalized client key:", norm_client_key)

    for idx, entry in enumerate(db):
        stored_key = entry.get("key")
        norm_stored_key = _norm(stored_key)

        print(f"[SERVER] Checking entry #{idx}")
        print("[SERVER]   Stored key:", repr(stored_key))
        print("[SERVER]   Norm stored:", norm_stored_key)

        if norm_stored_key == norm_client_key:
            print("[SERVER] MATCH: key found in DB")

            # Manual deactivation check
            if entry.get("active", True) is False:
                print("[SERVER] Deactivated key branch")
                return jsonify({"status": "denied", "msg": "This key has been deactivated"})

            # First activation = bind HWID
            if entry["used"] is False:
                print("[SERVER] First activation branch")
                entry["used"] = True
                entry["hwid"] = hwid
                save_db(db)
                return jsonify({"status": "ok", "msg": "Activated"})

            # Already used → check HWID
            if entry["hwid"] == hwid:
                print("[SERVER] Already activated branch")
                return jsonify({"status": "ok", "msg": "Already activated"})

            print("[SERVER] Used on another PC branch")
            return jsonify({"status": "denied", "msg": "Key already used on another PC"})

        else:
            print("[SERVER] No match with this entry, continuing...")

    print("[SERVER] Invalid key branch (no entries matched)")
    return jsonify({"status": "denied", "msg": "Invalid key"})


@app.route("/")
def home():
    return "ShinyFarm Licensing Server Running!"


if __name__ == "__main__":
    # For local testing, on Render you’ll use gunicorn instead
    app.run(host="0.0.0.0", port=5000)
