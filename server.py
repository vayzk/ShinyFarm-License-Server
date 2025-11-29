from flask import Flask, request, jsonify
import json
import os

DATABASE_FILE = "keys.json"
app = Flask(__name__)


def load_db():
    if not os.path.isfile(DATABASE_FILE):
        print("[DEBUG] keys.json not found, returning empty DB")
        return []
    with open(DATABASE_FILE, "r") as f:
        db = json.load(f)
    print(f"[DEBUG] Loaded DB with {len(db)} entries")
    return db


def save_db(db):
    with open(DATABASE_FILE, "w") as f:
        json.dump(db, f, indent=4)
    print("[DEBUG] DB saved to keys.json")


# Normalization helper (top-level so we can use in debug prints)
def _norm(k: str) -> str:
    if not isinstance(k, str):
        return ""
    return k.replace("-", "").upper()


@app.route("/validate", methods=["POST"])
def validate():
    data = request.json or {}
    key = data.get("key")
    hwid = data.get("hwid")

    print("\n========== /validate called ==========")
    print("[DEBUG] Raw client key:", repr(key))
    print("[DEBUG] Raw client hwid:", repr(hwid))

    if not key or not hwid:
        print("[DEBUG] Missing key or hwid branch")
        return jsonify({"status": "error", "msg": "Missing key or hwid"}), 400

    db = load_db()

    # Extra: if DB is empty, that's a huge red flag
    if not db:
        print("[DEBUG] WARNING: DB is empty. No keys to compare against.")

    # Precompute normalized client key once
    norm_client_key = _norm(key)
    print("[DEBUG] Normalized client key:", norm_client_key)

    for idx, entry in enumerate(db):
        stored_key = entry.get("key")
        norm_stored_key = _norm(stored_key)

        print(f"\n[DEBUG] Checking entry #{idx}")
        print("[DEBUG] Stored key:", repr(stored_key))
        print("[DEBUG] Normalized stored key:", norm_stored_key)

        # --- KEY COMPARISON ---
        print("[DEBUG] Comparing normalized keys...")
        print(f"[DEBUG]   client : {norm_client_key}")
        print(f"[DEBUG]   stored : {norm_stored_key}")

        if norm_stored_key == norm_client_key:
            print("[DEBUG] MATCH: key found in DB")

            # Manual deactivation check
            if entry.get("active", True) is False:
                print("[DEBUG] Deactivated key branch")
                return jsonify({"status": "denied", "msg": "This key has been deactivated"})

            # First activation = bind HWID
            if entry["used"] is False:
                print("[DEBUG] First activation branch")
                entry["used"] = True
                entry["hwid"] = hwid
                save_db(db)
                return jsonify({"status": "ok", "msg": "Activated"})

            # Already used → check HWID
            if entry["hwid"] == hwid:
                print("[DEBUG] Already activated branch")
                return jsonify({"status": "ok", "msg": "Already activated"})

            print("[DEBUG] Used on another PC branch")
            return jsonify({"status": "denied", "msg": "Key already used on another PC"})

        else:
            print("[DEBUG] No match for this entry, continuing...")

    print("[DEBUG] Invalid key branch (no entries matched)")
    return jsonify({"status": "denied", "msg": "Invalid key"})


@app.route("/")
def home():
    return "ShinyFarm Licensing Server Running!"


if __name__ == "__main__":
    app.run()
