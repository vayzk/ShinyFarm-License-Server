from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

KEYFILE = "keys.json"


def load_keys():
    if not os.path.exists(KEYFILE):
        return []
    with open(KEYFILE, "r") as f:
        return json.load(f)


def save_keys(keys):
    with open(KEYFILE, "w") as f:
        json.dump(keys, f, indent=4)


@app.route("/get_keys", methods=["GET"])
def get_keys():
    """Client lädt keys.json über GitHub, NICHT hier — aber als Fallback"""
    return jsonify(load_keys())


@app.route("/validate", methods=["POST"])
def validate():
    data = request.json

    if "key" not in data or "hwid" not in data:
        return jsonify({"success": False, "message": "Missing fields"})

    key_input = data["key"]
    hwid_input = data["hwid"]

    keys = load_keys()

    for entry in keys:
        if entry["key"] == key_input:

            if not entry["active"]:
                return jsonify({"success": False, "message": "Key deactivated"})

            # HWID check
            if entry["used"] and entry["hwid"] != hwid_input:
                return jsonify({"success": False, "message": "Key already used on another PC"})

            # Assign HWID
            entry["used"] = True
            entry["hwid"] = hwid_input
            save_keys(keys)

            return jsonify({"success": True, "message": "OK"})

    return jsonify({"success": False, "message": "Invalid key"})


@app.route("/")
def index():
    return "ShinyFarm License Server Running!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
