from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from bot import get_reply

app = Flask(__name__)


@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.form.get("Body", "").strip()
    sender = request.form.get("From", "")

    reply_text = get_reply(sender, incoming_msg)

    resp = MessagingResponse()
    resp.message(reply_text)
    return str(resp)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
