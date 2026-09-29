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
    add_reschedule_request_arguments = FunctionTool(
        name="add_reschedule_request_arguments",
        parameters={
            "type": "object",
            "properties": {
                "original_appointment_day": {
                    "type": "string",
                    "description": "the day the original appointment was scheduled for."
                },
                "new_appointment_day": {
                    "type": "string",
                    "description": "the day the user wants to reschedule to. Usually comes after the original appointment day is mentioned."
                },
                "start_time": {
                    "type": "string",
                    "description": "the starting time of the new appointment. Structured \'HH:MM\'. Example: \'10:00\', \'15:00\'"
                },
                "end_time": {
                    "type": "string",
                    "description": "the ending time of the new appointment. If not mentioned, recomfirm with the user what end time they would want. Structured \'HH:MM\'. Example: \'10:00\', \'15:00\'"
                }
            },
            "required": ["original_appointment_day", "new_appointment_day", "start_time", "end_time"],
            "additionalProperties": False
        },
        description="Gather necessary information to add a temporary rescheduled appointment to the database. gathers the original appointment day, the new rescheduled day, the new start-time, and new end-time.",
        strict=True
    )
    approve_request_arguments = FunctionTool(
        name="approve_request_arguments",
        parameters={
            "type": "object",
            "properties": {
                "student_name": {
                    "type": "string",
                    "description": "the day the original appointment was scheduled for."
                 },
                 "approval": {
                    "type": "boolean",
                    "description": "The tutor's approval or dissapproval of the temporary rescheduling. approved = True, denied = False"
                },
                "temp_id": {
                    "type": ["integer", "null"],
                    "description": "the id number of the rescheduled appointment. Not necessary initially. Only fill this argument in when the student name is not enough to find the temporary appointment."
                }
            },
            "required": ["student_name", "approval", "temp_id"],
            "additionalProperties": False
        },
        description="Gather information necessary to approve the rescheduling of an appointment. Gather the student name, approval, and, only if needed, the temp_id",
        strict=True
    )
    
    tools = [view_app_arguments, add_student_arguments, add_app_arguments, add_reschedule_request_arguments, approve_request_arguments]
    return tools