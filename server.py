from flask import Flask, request, jsonify
import json
import os
import base64
import requests

app = Flask(__name__)

# --------------------------------------------------------
#   CONFIG
# --------------------------------------------------------
KEYS_FILE = "keys.json"

# GitHub config (MUSS ausgefüllt sein!)
GITHUB_USER = "vayzk"
REPO_NAME = "ShinyFarm-License-Server"
FILE_PATH = "keys.json"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # bei Render unter "Environment Variables" setzen!


# --------------------------------------------------------
#   LOAD & SAVE
# --------------------------------------------------------
def load_db():
    if not os.path.isfile(KEYS_FILE):
        return []
    with open(KEYS_FILE, "r") as f:
        return json.load(f)


def save_db(db):
    with open(KEYS_FILE, "w") as f:
        json.dump(db, f, indent=4)


# --------------------------------------------------------
#   GITHUB SYNC
# --------------------------------------------------------
def github_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }


def github_download_sha():
    """Get SHA for keys.json so GitHub allows overwriting."""
    url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/{FILE_PATH}"
    r = requests.get(url, headers=github_headers())
    if r.status_code == 200:
        return r.json()["sha"]
    return None


def github_upload_keys(keys):
    """Upload updated keys.json to GitHub."""
    sha = github_download_sha()
    if sha is None:
        print("❌ GitHub: Failed to fetch SHA")
        return

    url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/{FILE_PATH}"

    encoded = base64.b64encode(json.dumps(keys, indent=4).encode()).decode()

    payload = {
        "message": "Auto update keys.json (ShinyFarm server)",
        "content": encoded,
        "sha": sha
    }

    r = requests.put(url, headers=github_headers(), json=payload)
    if r.status_code in (200, 201):
        print("✅ GitHub keys.json updated successfully")
    else:
        print("❌ GitHub upload failed:", r.text)


# --------------------------------------------------------
#   VALIDATION ENDPOINT
# --------------------------------------------------------
@app.route("/validate", methods=["POST"])
def validate():
    data = request.get_json()

    key = data.get("key")
    hwid = data.get("hwid")

    if not key or not hwid:
        return jsonify({"status": "error", "msg": "Key or HWID missing"}), 400

    db = load_db()

    for entry in db:
        if entry["key"] == key:

            # Deactivated key?
            if entry.get("active", True) is False:
                return jsonify({"status": "denied", "msg": "Key deactivated"})

            # First time activation → set HWID
            if entry["used"] is False:
                entry["used"] = True
                entry["hwid"] = hwid

                save_db(db)
                github_upload_keys(db)        # <── HIER passiert die Magie

                return jsonify({"status": "ok"})

            # Already used on THIS PC
            if entry["hwid"] == hwid:
                return jsonify({"status": "ok"})

            # Already used on OTHER PC
            return jsonify({"status": "denied", "msg": "Key already used on another PC"})

    return jsonify({"status": "denied", "msg": "Invalid key"})


# --------------------------------------------------------
#   LIST KEYS ENDPOINT (for KEY_MANAGER)
# --------------------------------------------------------
@app.route("/keys", methods=["GET"])
def get_keys():
    db = load_db()
    return jsonify(db)


# --------------------------------------------------------
#   ROOT
# --------------------------------------------------------
@app.route("/", methods=["GET"])
def home():
    return "ShinyFarm License Server Running"


# --------------------------------------------------------
#   RUN
# --------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
