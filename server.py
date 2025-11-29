from flask import Flask, request, jsonify
import json
import os
import base64
import requests

app = Flask(__name__)

# --------------------------------------------------------
#   SETTINGS
# --------------------------------------------------------
# Lokale Datei auf dem Server (Render)
KEYS_FILE = "keys.json"

# GitHub Repo Einstellungen
GITHUB_USER = "vayzk"
REPO_NAME = "ShinyFarm-License-Server"
FILE_PATH = "keys.json"

# In Render unter "Environment Variables" hinzufügen
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


# --------------------------------------------------------
#   HELPERS – LOAD / SAVE
# --------------------------------------------------------
def load_db():
    if not os.path.isfile(KEYS_FILE):
        return []
    with open(KEYS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(db):
    with open(KEYS_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)


# --------------------------------------------------------
#   GITHUB FUNCTIONS (SYNC keys.json)
# --------------------------------------------------------
def github_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }


def github_download_sha():
    """
    Holt die SHA des aktuellen keys.json auf GitHub.
    GitHub verlangt diese SHA, um Dateien zu überschreiben.
    """
    url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/{FILE_PATH}"
    r = requests.get(url, headers=github_headers())

    if r.status_code == 200:
        return r.json()["sha"]

    print("❌ Fehler: SHA konnte nicht geladen werden:", r.text)
    return None


def github_upload_keys(keys):
    """
    Lädt keys.json zum GitHub Repository hoch.
    """
    if not GITHUB_TOKEN:
        print("❌ Kein GitHub Token gesetzt!")
        return

    sha = github_download_sha()
    if sha is None:
        print("❌ GitHub SHA fehlgeschlagen.")
        return

    url = f"https://api.github.com/repos/{GITHUB_USER}/{REPO_NAME}/contents/{FILE_PATH}"

    # keys.json in Base64 encodieren
    encoded = base64.b64encode(json.dumps(keys, indent=4).encode()).decode()

    payload = {
        "message": "Auto update keys.json (ShinyFarm server)",
        "content": encoded,
        "sha": sha
    }

    r = requests.put(url, headers=github_headers(), json=payload)

    if r.status_code in (200, 201):
        print("✅ GitHub keys.json erfolgreich aktualisiert.")
    else:
        print("❌ GitHub Upload Fehler:", r.text)


# --------------------------------------------------------
#   VALIDATION ENDPOINT
# --------------------------------------------------------
@app.route("/validate", methods=["POST"])
def validate_key():
    data = request.get_json()

    key = data.get("key")
    hwid = data.get("hwid")

    if not key or not hwid:
        return jsonify({"status": "error", "msg": "Key or HWID missing"}), 400

    db = load_db()

    for entry in db:
        if entry["key"] == key:

            # Deaktivierter Key?
            if entry.get("active", True) is False:
                return jsonify({"status": "denied", "msg": "Key deactivated"})

            # ERSTE Aktivierung → HWID setzen
            if entry["used"] is False:
                entry["used"] = True
                entry["hwid"] = hwid

                save_db(db)          # Lokal speichern (Render)
                github_upload_keys(db)  # Und auf GitHub synchronisieren ★★ WICHTIG ★★

                return jsonify({"status": "ok"})

            # Key erneut auf dem SELBEN PC → OK
            if entry["hwid"] == hwid:
                return jsonify({"status": "ok"})

            # Key wurde bereits auf ANDEREM Gerät benutzt
            return jsonify({"status": "denied", "msg": "Key already used on another PC"})

    return jsonify({"status": "denied", "msg": "Invalid key"})


# --------------------------------------------------------
#   SEND FULL KEYS (for key_manager.py)
# --------------------------------------------------------
@app.route("/keys", methods=["GET"])
def get_all_keys():
    db = load_db()
    return jsonify(db)


# --------------------------------------------------------
#   ROOT
# --------------------------------------------------------
@app.route("/", methods=["GET"])
def home():
    return "ShinyFarm License Server is running."


# --------------------------------------------------------
#   START SERVER
# --------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
