from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from database import Database
import inspect
import json
import os
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# Maximum number of tool-call rounds per user message before giving up.
MAX_TOOL_ROUNDS = 5

# Maps the agent's tool names to Database method names.
TOOL_METHODS = {
    "view_app_arguments": "process_view",
    "add_student_arguments": "add_new_student",
    "add_appointment_arguments": "add_new_app",
    "add_reschedule_request_arguments": "process_reschedule",
    "approve_request_arguments": "approve_appointment",
}


class FoundryModel():
    def __init__(self, data_dir=".", log_path="turn_log.jsonl"):
        endpoint = os.environ.get("FOUNDRYPROJECTENDPOINT")
        # retrieve azure foundry project
        self.project = AIProjectClient(
            endpoint=endpoint, #endpoint
            credential=DefaultAzureCredential()
        )
        self.openai = self.project.get_openai_client()
        self.agent_name = "message-reader"
        self.data_dir = data_dir   #where the CSVs live (tests point this at a temp dir)
        self.log_path = log_path   #JSONL turn log; set to None to disable

    #------------------------Model calls-----------------------------------
    def new_conversation(self):
        return self.openai.conversations.create().id

    def run_turn(self, input_, convo_id):
        """One call to the agent. Returns (response, tool_calls)."""
        response = self.openai.responses.create(
            input=input_,
            conversation=convo_id,
            extra_body={"agent_reference": {"name": self.agent_name, "type": "agent_reference"}},
        )
        tool_calls = [
            item for item in response.output
            if getattr(item, "type", None) == "function_call"
        ]
        return response, tool_calls

    #------------------------Tool dispatch-----------------------------------
    @staticmethod
    def dispatch(tool_name, raw_arguments, database):
        """
        Run one tool call against the database.
        Returns (result, error_type). error_type is None on success, otherwise one of
        'unknown_tool', 'invalid_json', 'schema_invalid', 'exception'.
        Errors are returned as strings so the model can see them and recover,
        instead of crashing the webhook.
        """
        method_name = TOOL_METHODS.get(tool_name)
        if method_name is None:
            return f"not a function call: {tool_name}", "unknown_tool"

        try:
            args = json.loads(raw_arguments or "{}")
        except json.JSONDecodeError as e:
            return f"Tool arguments were not valid JSON: {e}", "invalid_json"

        method = getattr(database, method_name)
        try:
            inspect.signature(method).bind(**args)
        except TypeError as e:
            return f"Invalid arguments for {tool_name}: {e}", "schema_invalid"

        try:
            return method(**args), None
        except Exception as e:
            print(f"tool {tool_name} raised {type(e).__name__}: {e}")
            return f"Tool {tool_name} failed: {type(e).__name__}: {e}", "exception"

    #------------------------Full turn (model + tools + logging)--------------
    def chat(self, message, convo_id, database, case_id=None):
        """
        Handle one user message end to end: call the agent, execute any tool
        calls (looping until the agent stops calling tools or the cap is hit),
        log the turn, and return the final reply text.
        """
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "case_id": case_id,
            "convo_id": convo_id,
            "user_id": database.user[0] if database.user else None,
            "user_message": message,
            "tool_calls": [],
            "model_calls": 0,
            "latency_s": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "hit_round_cap": False,
        }

        def timed_turn(input_):
            start = time.perf_counter()
            resp, calls = self.run_turn(input_, convo_id)
            record["latency_s"] += time.perf_counter() - start
            record["model_calls"] += 1
            usage = getattr(resp, "usage", None)
            if usage is not None:
                record["input_tokens"] += getattr(usage, "input_tokens", 0) or 0
                record["output_tokens"] += getattr(usage, "output_tokens", 0) or 0
            return resp, calls

        response, tool_calls = timed_turn(message)

        for round_num in range(1, MAX_TOOL_ROUNDS + 1):
            if not tool_calls:
                break
            input_list = []
            for tool_call in tool_calls:
                result, error_type = self.dispatch(tool_call.name, tool_call.arguments, database)
                record["tool_calls"].append({
                    "round": round_num,
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,   # raw string, as the model produced it
                    "result": result,
                    "error_type": error_type,
                })
                input_list.append({
                    "type": "function_call",
                    "call_id": tool_call.call_id,
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                })
                input_list.append({
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": json.dumps({"result": result}, default=str),
                })
            print("ai responding to result")
            response, tool_calls = timed_turn(input_list)
        else:
            # Loop finished without break: the agent still wanted more tools.
            if tool_calls:
                record["hit_round_cap"] = True

        if record["hit_round_cap"]:
            reply = "Sorry, I wasn't able to complete that request. Please try again."
        else:
            reply = response.output_text

        record["reply"] = reply
        record["latency_s"] = round(record["latency_s"], 3)
        self._log(record)
        print(f"Agent response: {reply}")
        return reply

    #------------------------Entry point used by the webhook-----------------
    def read_message(self, message, phone_num):
        print(message)
        print(phone_num)

        #add phone number check here
        database = Database(self.data_dir)
        if not database.find_user(phone_num):
            return None

        convo_id = database.get_convo_id()
        if not convo_id:
            convo_id = self.new_conversation()
            database.set_convo_id(convo_id)

        return self.chat(message, convo_id, database)

    #------------------------Logging-----------------------------------------
    def _log(self, record):
        if not self.log_path:
            return
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, default=str) + "\n")
        except Exception as e:
            # logging must never break the conversation
            print(f"failed to write turn log: {e}")
