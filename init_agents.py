#Creates (or updates) the Foundry agents
#Is run seperately from main.

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
import init_tools
import os
load_dotenv()
def init_agents():
    endpoint = os.environ.get("FOUNDRYPROJECTENDPOINT")
    project = AIProjectClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential()
    )
    
    tools = init_tools.build_tools()
    
    agent_instructions = ("You are a scheduling assistant. If the user wants to view their appointments, use the view_app_arguments tool to gather the necessary information. "
                          "If the user wants to add a new student to the database, use the add_student_arguments tool to gather the necessary information. "
                          "If the user wants to add a new appointment to the database and is a tutor, use the add_appointment_arguments tool to gather the necessary appointment information. "
                          "Otherwise, tell the user that you can only help with schedule related topics.")
    agent = project.agents.create_version(
        agent_name="message-reader",
        definition=PromptAgentDefinition(
            model="gpt-4o-mini",
            instructions=agent_instructions,
            tools=tools,
        ),
    )
    print(f"created {agent.name} model {agent.definition.model} version {agent.version}")
    return agent

if __name__ == "__main__":
    init_agents()