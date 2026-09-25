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
        self.tools = self._init_tools()
        self.agent = self._create_model()
        
    def _create_model(self):
        agent_instructions = ("You are a scheduling assistant. If the user wants to view their appointments, use the view_app_arguments tool to gather the necessary information. "
                              "If the user wants to add a new student to the database, use the add_student_arguments tool to gather the necessary information. "
                              "If the user wants to add a new appointment to the database and is a tutor, use the add_appointment_arguments tool to gather the necessary appointment information. "
                              "Otherwise, tell the user that you can only help with schedule related topics.")
        agent = self.project.agents.create_version(
            agent_name="message-reader",
            definition=PromptAgentDefinition(
                model="gpt-4o-mini",
                instructions=agent_instructions,
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
                            "description": "The filter the user wants to view their schedule with. 0 = their own schedule, 1 = the entire schedule, 2 = the schedule for the current day, 3 = the schedule for a specific student that is not the user."
                    },
                    "student_name": {
                        "type": ["string", "null"],
                        "description": "The first or full name of the student that the user wants to see the schedule for. Only fill this out if specificity = 3, otherwise leave as null."
                    }
                },
                "required": ["specificity", "student_name"],
                "additionalProperties": False
            },
            description="Determine the specific kind of schedule and appointments that the user wants to see.",
            strict=True
        )
        add_student_arguments = FunctionTool(
            name="add_student_arguments",
            parameters={
                "type": "object",
                "properties": {
                    "name": {
                            "type": "string",
                            "description": "The full name of the name of the student that the tutor wants to add."
                    },
                    "phone_number": {
                        "type": "string",
                        "description": "The phone number of the student."
                    }
                },
                "required": ["student_name", "phone_number"],
                "additionalProperties": False
            },
            description="Gather the new student's full name and phone number to add to the database.",
            strict=True
        )
        add_app_arguments = FunctionTool(
            name="add_appointment_arguments",
            parameters={
                "type": "object",
                "properties": {
                    "student_name": {
                            "type": "string",
                            "description": "The first or full name of the name of the student that the tutor wants to add."
                    },
                    "app_day": {
                        "type": "string",
                        "description": "the day the appointment is scheduled for."
                    },
                    "start_time": {
                        "type": "string",
                        "description": "the starting time of the appointment. Structured \'HH:MM\'. Example: \'10:00\', \'15:00\'"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "the ending time of the appointment. Structured \'HH:MM\'. Example: \'10:00\', \'15:00\'"
                    }
                },
                "required": ["student_name", "app_day", "start_time", "end_time"],
                "additionalProperties": False
            },
            description="For a new appointment to be added, gathers the student's name, the appointment day, the start time, and end time.",
            strict=True
        )

        tools = [view_app_arguments, add_student_arguments, add_app_arguments]
        return tools

    def read_message(self, message, phone_num):
        print(message)
        print(phone_num)
        
        #add phone number check here
        database = Database()
        user_found = database.find_user(phone_num)
        if not user_found:
            return None
        
        response = self.openai.responses.create(
            input=message,
            extra_body={"agent_reference": {"name": self.agent.name, "type": "agent_reference"}},
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
            extra_body={"agent_reference": {"name": self.agent.name, "type": "agent_reference"}},
        )
        print(f"Agent response: {follow_up.output_text}")
        return follow_up.output_text
