from sinch import SinchClient
from flask import Flask, request, jsonify
from foundry_module import FoundryModel
import requests, base64
from dotenv import load_dotenv

import os
load_dotenv()
class SinchModule():
    def __init__(self):
        load_dotenv()
        
        self.foundry_module = FoundryModel()
        # retrieve sinch client information
        self.sinch_client = SinchClient(
            key_id = os.environ.get("SINCHUSER"),
            key_secret = os.environ.get('SINCHPASSWORD'),
            project_id = os.environ.get('SINCHPROJECTID'),
            conversation_region="us"
        )
        self.url = f"https://us.conversation.api.sinch.com/v1/projects/{os.environ.get('SINCHPROJECTID')}/messages:send"
    
    
    def webhook(self):
        data = request.json
        
        #message information extraction
        message = data.get("message", {})
        text = message.get("contact_message", {}).get("text_message", {}).get("text", "")
        channel = message.get("channel_identity", {}).get("channel", "SMS")
        sender_identity = message.get("channel_identity", {}).get("identity", "")
        
        print(f"Received from {sender_identity} via {channel}: {text}")
        self.main(text, sender_identity)
        
        return jsonify({"status": "ok"}), 200
    
    def main(self, text, sender_identity):
        return_message = self.foundry_module.read_message(text, sender_identity)
        if not return_message:
            return None
        self.send_text(return_message, sender_identity)
        
    def send_text(self, return_message, sender_identity):
        sender_identity = str(sender_identity)
        return_message = str(return_message)
        number = str(os.environ.get('SINCHPHONENUMBER'))
        print(f"----------return message-----------\n{return_message}")
        app_id = os.environ.get('SINCHAPPID')
        payload = {
            "app_id": app_id,
            "recipient": {
                "identified_by": {
                "channel_identities": [
                    {
                    "channel": "SMS",
                    "identity": sender_identity
                    }
                ]
                }
            },
            "message": {
                "text_message": {
                "text": return_message
                }
            },
            "channel_properties": {"SMS_SENDER": number}
        }
        headers = {"Content-Type": "application/json"}

        response = requests.post(self.url, json=payload, headers=headers, 
        auth=(os.environ.get('SINCHUSER'), os.environ.get('SINCHPASSWORD')))

        data = response.json()
        print("SEND STATUS:", response.status_code)
        print("SEND BODY:", response.text)
        print(data)
        
app = Flask(__name__)
module = SinchModule()
app.add_url_rule("/webhook", "webhook", module.webhook, methods=["POST"])
if __name__ == "__main__":
    module = SinchModule()
    #app.run(host="0.0.0.0", port=5000)
    module.main("Hello, can I see an appointment?", "+13104069080")
    print("hello!")
    
    #reschedule 1 14:00 15:00