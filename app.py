from flask import Flask, request, jsonify, render_template
from bot import get_reply

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"reply": "re?"}), 400

    # Use a fixed session key for browser (single-user webapp)
    reply = get_reply("webapp_user", message)
    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
