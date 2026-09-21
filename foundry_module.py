from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, Tool, FunctionTool
from azure.identity import DefaultAzureCredential
from openai import OpenAI
from dotenv import load_dotenv
import os
load_dotenv()
class FoundryModel():
    def __init__(self):
        # retrieve azure foundry project
        self.project = AIProjectClient(
            endpoint=os.environ.get("FOUNDRYENDPOINT"), #endpoint
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
                        "type": "int",
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
        
        response = self.openai.responses.create(
            input=message,
            extra_body={"agent_reference": {"name": self.agent.name, "type": "agent_reference"}},
        )
        
        print(f"answer: {response.output[0]}")
