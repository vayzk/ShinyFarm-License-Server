from flask import Flask, request, jsonify
import json
import os
import hmac
import hashlib

app = Flask(__name__)

KEYFILE = "keys.json"

# --------------------------------------------
# SECRET KEY MUSS IDENTISCH MIT CLIENT SEIN!
# --------------------------------------------
SECRET_KEY_HEX = "4d595f53555045525f5f5345435245545f4b45595f313233343536373839"
SECRET_KEY = bytes.fromhex(SECRET_KEY_HEX)


# --------------------------------------------
# LOAD / SAVE KEYS.JSON
# --------------------------------------------
def load_keys():
    if not os.path.exists(KEYFILE):
        return []
    with open(KEYFILE, "r") as f:
        return json.load(f)


def save_keys(keys):
    with open(KEYFILE, "w") as f:
        json.dump(keys, f, indent=4)


# --------------------------------------------
# VERIFY KEY SIGNATURE (server-side safety check)
# --------------------------------------------
def verify_key_signature(key: str):
    clean = key.replace("-", "").upper()
    if len(clean) != 22:
        return False

    payload = clean[:16]
    sig = clean[16:]

    digest = hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).hexdigest().upper()
    return sig == digest[:6]


# --------------------------------------------
# VALIDATION ENDPOINT (CLIENT CALLS THIS)
# --------------------------------------------
@app.route("/validate", methods=["POST"])
def validate():
    data = request.json

    if "key" not in data or "hwid" not in data:
        return jsonify({"status": "error", "msg": "Missing fields"}), 400

    key_input = data["key"].upper().strip()
    hwid_input = data["hwid"]

    # SERVER SIGNATURE CHECK
    if not verify_key_signature(key_input):
        return jsonify({"status": "error", "msg": "Invalid key signature"}), 403

    keys = load_keys()

    for entry in keys:
        if entry["key"] == key_input:

            # Deactivated?
            if not entry.get("active", True):
                return jsonify({"status": "error", "msg": "Key deactivated"}), 403

            # Already activated on another HWID?
            if entry.get("used", False) and entry.get("hwid") != hwid_input:
                return jsonify({"status": "error", "msg": "Key already used on another PC"}), 403

            # FIRST activation
            entry["used"] = True
            entry["hwid"] = hwid_input
            save_keys(keys)

            return jsonify({"status": "ok", "msg": "OK"}), 200

    return jsonify({"status": "error", "msg": "Invalid key"}), 404


# --------------------------------------------
# HOME
# --------------------------------------------
@app.route("/")
def index():
    return "ShinyFarm License Server Running!"


# --------------------------------------------
# RUN SERVER
# --------------------------------------------
if __name__ == "__main__":
    # Sollte auf 0.0.0.0 laufen, damit public erreichbar
    app.run(host="0.0.0.0", port=10000)
