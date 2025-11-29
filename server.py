from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

KEYFILE = "keys.json"


# -------------------------------------------------
# KEYS LOADING / SAVING
# -------------------------------------------------
def load_keys():
    if not os.path.exists(KEYFILE):
        return []
    with open(KEYFILE, "r") as f:
        return json.load(f)


def save_keys(keys):
    with open(KEYFILE, "w") as f:
        json.dump(keys, f, indent=4)


# -------------------------------------------------
# VALIDATION ENDPOINT (Client uses this)
# -------------------------------------------------
@app.route("/validate", methods=["POST"])
def validate():
    data = request.json

    if "key" not in data or "hwid" not in data:
        return jsonify({"status": "error", "msg": "Missing fields"})

    key_input = data["key"]
    hwid_input = data["hwid"]

    keys = load_keys()

    for entry in keys:

        if entry["key"] == key_input:

            # Check deactivated keys
            if not entry.get("active", True):
                return jsonify({"status": "error", "msg": "Key deactivated"})

            # HWID already assigned to someone else?
            if entry.get("used", False) and entry.get("hwid") != hwid_input:
                return jsonify({"status": "error", "msg": "Key already used on another PC"})

            # Assign HWID if unused
            entry["used"] = True
            entry["hwid"] = hwid_input
            save_keys(keys)

            return jsonify({"status": "ok", "msg": "OK"})

    return jsonify({"status": "error", "msg": "Invalid key"})


@app.route("/")
def index():
    return "ShinyFarm License Server Running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
