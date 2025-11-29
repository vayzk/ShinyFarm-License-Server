from flask import Flask, request, jsonify
import requests
import base64
import json
import hmac
import hashlib
import os

app = Flask(__name__)

# ==============================================================
# CONFIG – HIER EINTRAGEN
# ==============================================================

GITHUB_USER = "vayzk"
REPO_NAME = "ShinyFarm-License-Server"
FILE_PATH = "keys.json"

# GitHub Token MUSS als Umgebungsvariable gesetzt sein!
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN ist nicht gesetzt! (Render → Environment Variables)")

SECRET_KEY_HEX = "4d595f53555045525f5f5345435245545f4b45595f313233343536373839"
SECRET_KEY = bytes.fromhex(SECRET_KEY_HEX)

# ==============================================================
# GitHub API Helpers
# ==============================================================

def headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }


def download_keys():
    url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/{FILE_PATH}"
    r = requests.get(url, headers=headers())

    if r.status_code != 200:
        print("❌ DOWNLOAD FAILED:", r.text)
        return None, None

    data = r.json()
    sha = data["sha"]
    decoded = base64.b64decode(data["content"]).decode("utf-8")

    try:
        keys = json.loads(decoded)
    except:
        print("❌ JSON ERROR IN GITHUB FILE")
        return None, None

    return keys, sha


def upload_keys(keys, sha):
    url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/{FILE_PATH}"

    encoded = base64.b64encode(json.dumps(keys, indent=4).encode()).decode()

    payload = {
        "message": "Update via License Server",
        "content": encoded,
        "sha": sha
    }

    r = requests.put(url, headers=headers(), json=payload)

    if r.status_code in (200, 201):
        print("✅ keys.json updated on GitHub")
        return True
    else:
        print("❌ UPLOAD FAILED:", r.text)
        return False


# ==============================================================
# Verify Key Signature
# ==============================================================

def verify_key_signature(key: str) -> bool:
    clean = key.replace("-", "").upper()

    if len(clean) != 22:
        return False

    payload = clean[:16]
    sig = clean[16:]

    digest = hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).hexdigest().upper()
    return sig == digest[:6]


# ==============================================================
# VALIDATION ENDPOINT (CLIENT CALLS THIS)
# ==============================================================

@app.route("/validate", methods=["POST"])
def validate():
    data = request.json

    if "key" not in data or "hwid" not in data:
        return jsonify({"status": "error", "msg": "Missing key or hwid"}), 400

    key_input = data["key"].strip().upper()
    hwid_input = data["hwid"]

    # Check signature
    if not verify_key_signature(key_input):
        return jsonify({"status": "error", "msg": "Invalid key signature"}), 403

    # Load keys.json from GitHub
    keys, sha = download_keys()
    if keys is None:
        return jsonify({"status": "error", "msg": "Cannot load keys.json"}), 500

    for entry in keys:
        if entry["key"].upper() == key_input:

            # Deactivated?
            if not entry.get("active", True):
                return jsonify({"status": "error", "msg": "Key deactivated"}), 403

            # Already used on another device?
            if entry.get("used", False) and entry.get("hwid") != hwid_input:
                return jsonify({"status": "error", "msg": "Key already used on another PC"}), 403

            # FIRST activation
            entry["used"] = True
            entry["hwid"] = hwid_input

            # Upload back to GitHub
            upload_keys(keys, sha)

            return jsonify({"status": "ok", "msg": "OK"}), 200

    return jsonify({"status": "error", "msg": "Invalid key"}), 404


# ==============================================================
# HOME
# ==============================================================

@app.route("/")
def index():
    return "ShinyFarm License Server Running!"


# ==============================================================
# RUN SERVER
# ==============================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
