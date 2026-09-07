from openai import OpenAI
from dotenv import load_dotenv
import os
load_dotenv()

endpoint = "https://comps-schedule-agents.services.ai.azure.com/openai/v1"
deployment_name = "gpt-4o-mini"
api_key = os.environ.get("FOUNDRYAPIKEY")

client = OpenAI(
    base_url=endpoint,
    api_key=api_key
)

response = client.responses.create(
    model=deployment_name,
    input="What is the capital of France?",
)

print(f"answer: {response.output[0]}")
