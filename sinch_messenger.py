from sinch import SinchClient
from flask import Flask, request, jsonify
import requests, base64
from dotenv import load_dotenv
import os
load_dotenv()

project_id = os.environ.get('SINCHPROJECTID')
region = "US"
url = f"https://US.conversation.api.sinch.com/v1/projects/{project_id}/messages:send"
phone_num = os.environ.get('PHONENUM')
app_id = os.environ.get('SINCHAPPID')
payload = {
  "app_id": app_id,
  "recipient": {
    "identified_by": {
      "channel_identities": [
        {
          "channel": "SMS",
          "identity": phone_num
        }
      ]
    }
  },
  "message": {
    "text_message": {
      "text": "test text"
    }
  },
  "channel_properties": {}
}

headers = {"Content-Type": "application/json"}

response = requests.post(url, json=payload, headers=headers, 
auth=(os.environ.get('SINCHUSER'), os.environ.get('SINCHPASSWORD')))

data = response.json()
print(data)

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    
    #message information extraction
    message = data.get("message", {})
    text = message.get("contact_message", {}).get("text_message", {}).get("text", "")
    channel = message.get("channel_identity", {}).get("channel", "SMS")
    sender_identity = message.get("channel_identity", {}).get("identity", "")
    
    print(f"Received from {sender_identity} via {channel}: {text}")
    
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(port=3000)