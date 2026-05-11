from flask import Flask, request, jsonify, render_template
import traceback
from bot import get_reply

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or request.form.get("message") or "").strip()
    if not message:
        return jsonify({"reply": "re?"}), 400

    try:
        reply = get_reply("webapp_user", message)
        return jsonify({"reply": reply})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"reply": f"[error] {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
