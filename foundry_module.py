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
        self.database = Database()
        endpoint = os.environ.get("FOUNDRYPROJECTENDPOINT")
        # retrieve azure foundry project
        self.project = AIProjectClient(
            endpoint=endpoint, #endpoint
            credential=DefaultAzureCredential()
        )
        self.openai = self.project.get_openai_client()
        self.tools = self._init_tools()
        self.agent = self._create_model()
        
    def _create_model(self):
        agent = self.project.agents.create_version(
            agent_name="message-reader",
            definition=PromptAgentDefinition(
                model="gpt-4o-mini",
                instructions="You are a scheduling assistant. If the user wants to view their appointments, use the view_app_arguments tool to gather the necessary information. Otherwise, tell the user that you can only help with schedule related topics.",
                tools=self.tools,
            ),
        )
        print("Agent name:", agent.name)
        print("Agent model:", agent.definition.model)
        
        return agent
    
    def _init_tools(self):
        view_app_arguments = FunctionTool(
            name="view_app_arguments",
            parameters={
                "type": "object",
                "properties": {
                    "specificity": {
                            "type": "integer",
                            "description": "The filter the user wants to view their schedule with. 0 = their own schedule, 1 = the entire schedule, 2 = the schedule for the current day."
                    }
                },
                "required": ["specificity"],
                "additionalProperties": False
            },
            description="Determine the specific kind of schedule and appointments that the user wants to see.",
            strict=True
        )

        tools = [view_app_arguments]
        return tools

    def read_message(self, message, phone_num):
        print(message)
        print(phone_num)
        
        #add phone number check here
        
        response = self.openai.responses.create(
            input=message,
            extra_body={"agent_reference": {"name": self.agent.name, "type": "agent_reference"}},
        )
        
        #Model may need multiple attempts to generate response, retry up to 5 times.
        for r in range(5):
            function_calls = [item for item in response.output if item.type == "function_call"]
            if not function_calls:
                break

            input_list: ResponseInputParam = []
            for item in function_calls:
                if item.name == "view_app_arguments":
                    result = self.database.process_view(**json.loads(item.arguments))
                else:
                    result = f"Unknown function: {item.name}"

                input_list.append(
                    FunctionCallOutput(
                    type="function_call_output",
                    call_id=item.call_id,
                    output=json.dumps({"result": result}),
                    )
                )
        response = self.openai.responses.create(
            input=input_list,
            conversation=self.conversation.id,
            extra_body={"agent_reference": {"name": self.agent.name, "type": "agent_reference"}},
        )
        print(f"Agent response: {response.output_text}")
        return response
