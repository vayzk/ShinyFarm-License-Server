from flask import Flask, request, jsonify
import json
import os

DATABASE_FILE = "keys.json"
app = Flask(__name__)

def load_db():
    if not os.path.isfile(DATABASE_FILE):
        return []
    with open(DATABASE_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DATABASE_FILE, "w") as f:
        json.dump(db, f, indent=4)

@app.route("/validate", methods=["POST"])
def validate():
    data = request.json
    key = data.get("key")
    hwid = data.get("hwid")

    if not key or not hwid:
        return jsonify({"status": "error", "msg": "Missing key or hwid"}), 400

    db = load_db()

    for entry in db:
        if entry["key"] == key:

            # ✅ Manual deactivation check (this was missing)
            if entry.get("active", True) is False:
                return jsonify({"status": "denied", "msg": "This key has been deactivated"})

            # First activation = bind HWID
            if entry["used"] is False:
                entry["used"] = True
                entry["hwid"] = hwid
                save_db(db)
                return jsonify({"status": "ok", "msg": "Activated"})

            # Already used → check HWID
            if entry["hwid"] == hwid:
                return jsonify({"status": "ok", "msg": "Already activated"})

            return jsonify({"status": "denied", "msg": "Key already used on another PC"})

    return jsonify({"status": "denied", "msg": "Invalid key"})

@app.route("/")
def home():
    return "ShinyFarm Licensing Server Running!"

if __name__ == "__main__":
    app.run()
