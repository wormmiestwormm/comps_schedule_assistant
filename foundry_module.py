from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, Tool, FunctionTool
from openai.types.responses.response_input_param import FunctionCallOutput, ResponseInputParam
from azure.identity import DefaultAzureCredential
from database import Database
import json
from openai import OpenAI
from dotenv import load_dotenv
import os
load_dotenv()
class FoundryModel():
    def __init__(self):
        endpoint = os.environ.get("FOUNDRYPROJECTENDPOINT")
        # retrieve azure foundry project
        self.project = AIProjectClient(
            endpoint=endpoint, #endpoint
            credential=DefaultAzureCredential()
        )
        self.openai = self.project.get_openai_client()
        self.agent_name = "message-reader"

    def read_message(self, message, phone_num):
        print(message)
        print(phone_num)
        
        #add phone number check here
        database = Database()
        user_found = database.find_user(phone_num)
        if not user_found:
            return None
        
        convo_id = database.get_convo_id()
        if not convo_id:
            conversation = self.openai.conversations.create()
            convo_id = conversation.id
            database.set_convo_id(convo_id)
        
        response = self.openai.responses.create(
            input=message,
            conversation=convo_id,
            extra_body={"agent_reference": {"name": self.agent_name, "type": "agent_reference"}},
        )
        
        #Model may need multiple attempts to generate response, retry up to 5 times.
        tool_calls = [
            item for item in response.output
            if getattr(item, "type", None) == "function_call"
        ]
        if not tool_calls:
            return response.output_text
        input_list = []
        for tool_call in tool_calls:
            if tool_call.name == "view_app_arguments":
                result = database.process_view(**json.loads(tool_call.arguments))
            elif tool_call.name == "add_student_arguments":
                result = database.add_new_student(**json.loads(tool_call.arguments))
            elif tool_call.name == "add_appointment_arguments":
                pass
            else:
                result = f"not a function call: {tool_call.name}"

            input_list.append(
                {
                    "type": "function_call",
                    "call_id": tool_call.call_id,
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                }
            )

            input_list.append(
                {
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": json.dumps({"result": result}),
                }
            )
        print("ai responding to result")
        follow_up = self.openai.responses.create(
            input=input_list,
            conversation=convo_id,
            extra_body={"agent_reference": {"name": self.agent_name, "type": "agent_reference"}},
        )
        print(f"Agent response: {follow_up.output_text}")
        return follow_up.output_text
