"""
Tool schemas and agent instructions shared between the one-time agent setup
script (init_agents.py) and the runtime orchestration code (foundry_model.py).
"""

from azure.ai.projects.models import Tool, FunctionTool

def build_tools():
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