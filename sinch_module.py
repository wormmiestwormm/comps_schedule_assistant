from sinch import SinchClient
from flask import Flask, request, jsonify
from database import Database
import requests, base64
from dotenv import load_dotenv

import os
load_dotenv()
class SinchModule():
    def __init__(self):
        load_dotenv()
        
        self.database = Database()
        # retrieve sinch client information
        self.sinch_client = SinchClient(
            key_id = os.environ.get("SINCHAPPID"),
            key_secret = os.environ.get('SINCHPASSWORD'),
            project_id = os.environ.get('SINCHPROJECTID'),
            conversation_region="us"
        )
        self.url = f"https://US.conversation.api.sinch.com/v1/projects/{os.environ.get('SINCHPROJECTID')}/messages:send"
    
    app = Flask(__name__)
    @app.route("/webhook", methods=["POST"])
    def webhook(self):
        data = request.json
        
        #message information extraction
        message = data.get("message", {})
        text = message.get("contact_message", {}).get("text_message", {}).get("text", "")
        channel = message.get("channel_identity", {}).get("channel", "SMS")
        sender_identity = message.get("channel_identity", {}).get("identity", "")
        
        print(f"Received from {sender_identity} via {channel}: {text}")
        self.database.read_message(message, sender_identity)
        
        return jsonify({"status": "ok"}), 200
    
    def main(self, text, channel, sender_identity):
        return_message = self.foundry_model.start_conversation(text, channel, sender_identity)
        self.send_text(return_message)
        
    def send_text(self, return_message):
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
                "text": return_message
                }
            },
            "channel_properties": {}
        }
        headers = {"Content-Type": "application/json"}

        response = requests.post(self.url, json=payload, headers=headers, 
        auth=(os.environ.get('SINCHUSER'), os.environ.get('SINCHPASSWORD')))

        data = response.json()
        print(data)

if __name__ == "__main__":
    module = SinchModule()
    module.main("test message not from sinch", "SMS", "+13104069080")