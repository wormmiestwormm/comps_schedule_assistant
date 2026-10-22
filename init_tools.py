"""
Tool schemas and agent instructions shared between the one-time agent setup
script (init_agents.py) and the runtime orchestration code (foundry_module.py).

IMPORTANT: every parameter name below must match the argument names of the Database method
the tool is dispatched to (see TOOL_METHODS in foundry_module.py). Run `python eval/check_tools.py`
after editing to verify.
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
                        "description": "The filter the user wants to view their schedule with. 0 = their own schedule, 1 = the entire schedule (if the user asks for a schedule on a specific day, use this input), 2 = the schedule for the current day, 3 = the schedule for a specific student that is not the user. If the user asks for availability, input 1 or 2 depending on whether the user wants to view general availability or availability on a specific day."
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
                        "description": "The full name of the student that the tutor wants to add."
                },
                "phone_num": {
                    "type": "string",
                    "description": "The phone number of the student. Formatted as a string of 11 digits, and will always be 1. ex: \"13102149876\"."
                }
            },
            "required": ["name", "phone_num"],
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
                        "description": "The first or full name of the student that the appointment is for."
                },
                "day": {
                    "type": "string",
                    "description": "the day the appointment is scheduled for. Must be lowercase."
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
            "required": ["student_name", "day", "start_time", "end_time"],
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
                "o_app_day": {
                    "type": "string",
                    "description": "the day the original appointment was scheduled for. Must be lowercase."
                },
                "new_day": {
                    "type": "string",
                    "description": "the day the user wants to reschedule to. Usually comes after the original appointment day is mentioned. Must be lowercase."
                },
                "new_start": {
                    "type": "string",
                    "description": "the starting time of the new appointment. Structured \'HH:MM\'. Example: \'10:00\', \'15:00\'"
                },
                "new_end": {
                    "type": "string",
                    "description": "the ending time of the new appointment. If not mentioned, reconfirm with the user what end time they would want. Structured \'HH:MM\'. Example: \'10:00\', \'15:00\'"
                }
            },
            "required": ["o_app_day", "new_day", "new_start", "new_end"],
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
                    "description": "The first or full name of the student whose reschedule request is being approved or denied."
                },
                "approval": {
                    "type": "boolean",
                    "description": "The tutor's approval or disapproval of the temporary rescheduling. approved = True, denied = False"
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
    cancel_appointment_arguments = FunctionTool(
        name="cancel_appointment_arguments",
        parameters={
            "type": "object",
            "properties": {
                "student_name": {
                    "type": "string",
                    "description": "The first or full name of the student whose appointment is being canceled."
                },
                "day": {
                    "type": "string",
                    "description": "the day the appointment was scheduled for. Must be lowercase."
                },
            },
            "required": ["student_name", "day"],
            "additionalProperties": False
        },
        description="Gather information necessary to mark a regular appointment as canceled temporarily (that one occurrence only). Gather the student name and appointment day. DO NOT use this for permanent appointment removals.",
        strict=True
    )

    cancel_reschedule_arguments = FunctionTool(
        name="cancel_reschedule_arguments",
        parameters={
            "type": "object",
            "properties": {
                "student_name": {
                    "type": "string",
                    "description": "The first or full name of the student whose reschedule request is being canceled."
                },
                "temp_id": {
                    "type": ["integer", "null"],
                    "description": "the id number of the rescheduled appointment. Not necessary initially. Only fill this argument in when the student name is not enough to find the temporary appointment, otherwise leave as null."
                }
            },
            "required": ["student_name", "temp_id"],
            "additionalProperties": False
        },
        description="Gather information necessary to cancel a rescheduled appointment request. Gather the student name and, only if needed, the temp_id",
        strict=True
    )

    remove_appointment_arguments = FunctionTool(
        name="remove_appointment_arguments",
        parameters={
            "type": "object",
            "properties": {
                "student_name": {
                    "type": "string",
                    "description": "The first or full name of the student whose appointment is being permanently removed."
                },
                "day": {
                    "type": "string",
                    "description": "the day the appointment was scheduled for. Must be lowercase."
                },
                "app_id": {
                    "type": ["integer", "null"],
                    "description": "the id number of the appointment. Not necessary initially. Only fill this argument in when the student name and day are not enough to find the appointment, otherwise leave as null."
                }
            },
            "required": ["student_name", "day", "app_id"],
            "additionalProperties": False
        },
        description="Tutor only. Gather information necessary to PERMANENTLY remove a regular appointment from the schedule. Gather the student name, the appointment day and, only if needed, the app_id. DO NOT use this for one-time cancellations.",
        strict=True
    )
    #unused availability tool, not currently planned for implementation.
    """
    availability_arguments = FunctionTool(
        name="availability_arguments",
        parameters={
            "type": "object",
            "properties": {
                "day": {
                    "type": ["string", "null"],
                    "description": "The day the user wants to view availability for. May be left as null."
                },
            },
            "required": ["day"],
            "additionalProperties": False
        },
        description="Gather information necessary to view the time availability for potential reschedules or new appointments.",
        strict=True
    )
    """

    tools = [view_app_arguments, add_student_arguments, add_app_arguments, add_reschedule_request_arguments, approve_request_arguments,
             cancel_appointment_arguments, cancel_reschedule_arguments, remove_appointment_arguments]
    return tools