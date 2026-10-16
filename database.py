import csv
import os
import pandas as pd
from datetime import datetime

PEOPLE_CSV = "mock_people_database.csv"
SCHEDULE_CSV = "mock_schedule.csv"
TEMP_APPS_CSV = "mock_temp_apps.csv"

#Column positions in mock_people_database.csv.
#Inferred from find_user / get_convo_id / set_convo_id. If your CSV header
#differs, this is the only place that needs to change.
PEOPLE_ID = 0
PEOPLE_NAME = 1
PEOPLE_PHONE = 2
PEOPLE_ROLE = 3
PEOPLE_CONVO = 4
PEOPLE_NUM_COLS = 5


class Database:
    def __init__(self, data_dir="."):
        # data_dir lets tests point at a temp copy of the CSVs instead of
        # relying on the process working directory.
        self.data_dir = data_dir
        self.phone_num = None
        self.user = None
        self.og_app = None
        self.temp_app = None
        self.student = None
        self.notifications = [] #meant for sending text notifications to multiple people

    def _path(self, filename):
        return os.path.join(self.data_dir, filename)

    #------------------------Who is the sender-------------------------------------
    def is_tutor(self):
        return (self.user is not None and len(self.user) > PEOPLE_ROLE
                and self.user[PEOPLE_ROLE].strip().lower() == "tutor")

    def sender_context(self):
        """One-line sender description that is prepended to each user message for the agent."""
        if self.user is None:
            return None
        name = " ".join(str(self.user[PEOPLE_NAME]).replace("[", "").replace("]", "").split())
        role = self.user[PEOPLE_ROLE].strip().lower() if len(self.user) > PEOPLE_ROLE else "unknown"
        return f"[Sender: {name}, role: {role}]"

    @staticmethod
    def _next_id(df):
        # max existing id (first column) + 1. Unlike row-count based ids this
        # never skips values or collides with existing rows.
        ids = pd.to_numeric(df.iloc[:, 0], errors="coerce").dropna()
        return 0 if ids.empty else int(ids.max()) + 1

    #------------------------Getters and Setters-----------------------------------
    #find and set current user from database
    def find_user(self, phone_num):
        print("attempting to find user")
        print(phone_num)
        with open(self._path(PEOPLE_CSV), mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)

            #find user phone number in database
            for u in reader:
                if len(u) > PEOPLE_PHONE and u[PEOPLE_PHONE] == phone_num:
                    print(f"user is: {u[PEOPLE_NAME]}")
                    self.phone_num = phone_num
                    self.user = u
                    return True
        print(f"user {phone_num} not found")
        return False

    #the (single) tutor's row from the people CSV, or None if there isn't one
    def get_tutor(self):
        with open(self._path(PEOPLE_CSV), mode='r', encoding='utf-8') as file:
            for p in csv.reader(file):
                if len(p) > PEOPLE_ROLE and p[PEOPLE_ROLE].strip().lower() == "tutor":
                    return p
        return None

    #find student in database by name (for when a tutor needs to reference a specific student).
    def find_student(self, name):
        print(f"finding {name} in {PEOPLE_CSV}")
        with open(self._path(PEOPLE_CSV), mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)

            #find student in database
            for s in reader:
                if len(s) > PEOPLE_NAME and name.lower() in s[PEOPLE_NAME].lower():
                    print(f"student found: {s}")
                    self.student = s
                    return True
        print(f"student {name} not found")
        return False

    #verify that original appointment exists (the sender's own by default, or a given student's)
    def _find_og_app(self, ap_day, student_id=None):
        sid = str(student_id if student_id is not None else self.user[0])
        with open(self._path(SCHEDULE_CSV), mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[1] == sid and app[2] == ap_day:
                    self.og_app = app
                    print(f"original appointment on {ap_day} found")
                    return True
        print(f"original appointment on {ap_day} not found")
        return False

    #find the selected student's appointment by id. Ids arrive from the model as ints
    #but are strings in the CSV, so compare as strings.
    def _find_og_app_with_id(self, ap_id):
        with open(self._path(SCHEDULE_CSV), mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[1] == str(self.student[0]) and app[0] == str(ap_id):
                    self.og_app = app
                    print(f"original appointment {ap_id} found")
                    return True
        print(f"original appointment {ap_id} not found")
        return False

    #verify that temporary appointment exists (and, if student_id is given, that it belongs to that student)
    def _find_temp_app(self, temp_id, student_id=None):
        with open(self._path(TEMP_APPS_CSV), mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[0] == str(temp_id) and (student_id is None or app[2] == str(student_id)):
                    self.temp_app = app
                    print(f"temporary appointment {temp_id} found")
                    return True
        print(f"temporary appointment {temp_id} not found")
        return False

    #defence in depth: foundry_module.dispatch already blocks this, but the database layer should
    #never let a student act on somebody else's records even if it is called directly.
    def _acting_on_other_student(self):
        return (not self.is_tutor()) and self.student is not None and self.student[0] != self.user[0]

    #all temporary appointments belonging to the currently selected student
    def _find_student_temp_apps(self):
        found = []
        with open(self._path(TEMP_APPS_CSV), mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if len(app) > 2 and app[2] == self.student[0]:
                    found.append(app)
        # first row may be the header, which never matches a student id
        return found

    #Set conversation id if none exists already
    def set_convo_id(self, convo_id, person_id=None):
        # dtype=str: an empty convo_id column would otherwise load as float64
        # and reject a string value on current pandas versions.
        df = pd.read_csv(self._path(PEOPLE_CSV), dtype=str)
        df.columns = df.columns.str.strip()  # the header is ' convo_id' (leading space) in mock_people_database.csv
        pid = person_id if person_id is not None else self.user[PEOPLE_ID]
        df.loc[df['id'] == str(pid), 'convo_id'] = convo_id
        df.to_csv(self._path(PEOPLE_CSV), index=False)

    #get conversation id
    def get_convo_id(self):
        if self.user is not None and len(self.user) > PEOPLE_CONVO:
            return self.user[PEOPLE_CONVO]
        return None


    #----------------------View schedule methods----------------------
    def _convert_app_list_times(self, app_list):
        for app in app_list:
            if app[0] in ("app_id", "temp_id"):
                continue
            start_index, end_index = (4, 5) if len(app) > 5 else (3, 4)
            app[start_index], app[end_index] = self.convert_24_to_12h(
                app[start_index], app[end_index]
            )
        return app_list

    @staticmethod
    def _is_active_temp(app):
        # csv.reader yields strings, so compare against "1" / "0", not ints.
        return len(app) > 7 and str(app[6]) == "1" and str(app[7]) == "0" and app[1] != "canceled"

    def process_view(self, specificity=1, student_name=None):
        print("process_view accessed")
        if specificity == 0:
            print("individual schedule view")
            return self.return_indie_app_list(self.user)
        elif specificity == 1:
            print("complete schedule view")
            return self.return_complete_app_list()
        elif specificity == 2:
            print("day schedule view")
            return self.return_day_list()
        elif specificity == 3:
            print("student's schedule view")
            if not self.find_student(student_name):
                return f"student \'{student_name}\' not found in database."
            return self.return_indie_app_list(self.student)
        else:
            return "Error: specificity argument was not one of the established values, please try again."


    def return_complete_app_list(self):
        return_list = []
        og_app_ids = []
        with open(self._path(TEMP_APPS_CSV), mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[3] == "canceled" and str(app[7]) == "0":
                    og_app_ids.append(app[1])
                elif self._is_active_temp(app):
                    return_list.append(app)
                    og_app_ids.append(app[1])
        with open(self._path(SCHEDULE_CSV), mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[0] not in og_app_ids:
                    return_list.append(app)
        return self._convert_app_list_times(return_list)


    def return_day_list(self):
        # Days are assumed to be stored as full names ("Tuesday"), matching
        # what the reschedule tool passes in. Compared case-insensitively.
        curr_day = datetime.now().strftime("%A").lower()
        return_list = []
        og_app_ids = []
        with open(self._path(TEMP_APPS_CSV), mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[3] == "canceled" and str(app[7]) == "0":
                    og_app_ids.append(app[1])
                elif self._is_active_temp(app) and app[3].lower() == curr_day:
                    return_list.append(app)
                    og_app_ids.append(app[1])
        with open(self._path(SCHEDULE_CSV), mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                # schedule rows are [app_id, student_id, day, start, end]
                if len(app) > 2 and app[2].lower() == curr_day and app[0] not in og_app_ids:
                    return_list.append(app)
        return self._convert_app_list_times(return_list)


    #returns app or temp app for user
    def return_indie_app_list(self, person):
        return_list = []
        og_app_ids = []
        with open(self._path(TEMP_APPS_CSV), mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[3] == "canceled" and str(app[7]) == "0":
                    og_app_ids.append(app[1])
                elif len(app) > 2 and app[2] == person[0] and self._is_active_temp(app):
                    return_list.append(app)
                    og_app_ids.append(app[1])
        with open(self._path(SCHEDULE_CSV), mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[1] == person[0] and app[0] not in og_app_ids:
                    return_list.append(app)
        return self._convert_app_list_times(return_list)
    
    #returns app or temp app for user
    def return_student_app_list(self):
        return_list = []
        with open(self._path(SCHEDULE_CSV), mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[1] == self.student[0]:
                    return_list.append(app)
        return self._convert_app_list_times(return_list)

    #--------------------------Reschedule Process-----------------------------
    #check for conflicts with standard schedule AND any existing temp appointments
    def process_reschedule(self, o_app_day, new_day, new_start, new_end):
        if not self._find_og_app(o_app_day):
            return f"The user's appointment on {o_app_day} was not found. Please clarify with the user."

        conflict_check_result = self.check_conflicts(new_day, new_start, new_end)
        if conflict_check_result:
            return conflict_check_result
        return_message = self.append_new_temp_app(new_day, new_start, new_end)
        start, end = self.convert_24_to_12h(self.temp_app[4], self.temp_app[5])
        self._queue(self.get_tutor(), f"{self.user[PEOPLE_NAME]} asked to move their {o_app_day} appointment to {new_day} {start}-{end} (request #{self.temp_app[0]}). Reply to approve or deny.")
        return return_message


    def check_conflicts(self, new_day, new_start, new_end):
        og_app_id = self.og_app[0] if self.og_app else None

        with open(self._path(SCHEDULE_CSV), mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[0] == og_app_id:
                    continue
                if app[2] == new_day and (app[3] < new_end and app[4] > new_start):
                    return f"conflict with standard appointment {app[0]}"
        with open(self._path(TEMP_APPS_CSV), mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[1] == og_app_id:
                    continue
                if app[3] == new_day and (app[4] < new_end and app[5] > new_start):
                    return f"conflict with temporary appointment {app[0]}"
        return None


    #append new temp reschedule
    def append_new_temp_app(self, new_day, new_start, new_end):
        df = pd.read_csv(self._path(TEMP_APPS_CSV))
        id = self._next_id(df)
        ap_start, ap_end = self.convert_24_to_12h(new_start, new_end)  # raises on bad times, before anything is written
        new_temp_app = [id, self.og_app[0], self.user[0], new_day, new_start, new_end, 0, 0]
        print(f"new_temp_app: {new_temp_app}")
        with open(self._path(TEMP_APPS_CSV), mode='a', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(new_temp_app)

        self.temp_app = new_temp_app
        #will also return message for the tutor, requires second phone number though
        return f"Appointment for {self.og_app[0]} changed to {new_day}, {ap_start}-{ap_end}."
    
    def append_temp_cancel(self):
        df = pd.read_csv(self._path(TEMP_APPS_CSV))
        id = self._next_id(df)
        #student_id is the appointment's owner (og_app[1]), which is not always the sender:
        #a tutor can cancel on behalf of a student.
        new_temp_app = [id, self.og_app[0], self.og_app[1], "cancel", "00:00", "00:00", 1, 0]
        print(f"(canceled app) new_temp_app: {new_temp_app}")
        with open(self._path(TEMP_APPS_CSV), mode='a', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(new_temp_app)

    def _is_already_canceled(self, app_id):
        with open(self._path(TEMP_APPS_CSV), mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if self._is_active_temp(app) and app[1] == str(app_id) and app[3] == "cancel":
                    return True
        return False

    def cancel_appointment(self, student_name, day):
        if not self.find_student(student_name):
            return f"student \'{student_name}\' not found in database. Make sure the student is registered in the database first."
        if self._acting_on_other_student():
            return "Permission denied: students can only cancel their own appointments."

        if not self._find_og_app(day, self.student[0]):
            return f"{student_name}'s appointment on {day} was not found. Please clarify with the user."
        if self._is_already_canceled(self.og_app[0]):
            return f"The appointment on {day} is already canceled."

        self.append_temp_cancel()
        start, end = self.convert_24_to_12h(self.og_app[3], self.og_app[4])
        if self.is_tutor():
            text = f"Your tutor canceled your appointment on {day} {start}-{end}. Please consult them if you have any questions."
        else:
            text = f"{self.user[PEOPLE_NAME]} canceled their appointment on {day} {start}-{end}. Please discuss with them if you have any questions."
        self._queue(self._other_party(), text)
        return f"appointment on {day} successfully canceled temporarily."


    def cancel_reschedule_request(self, student_name, temp_id=None):
        if not self.find_student(student_name):
            return f"student \'{student_name}\' not found in database. Make sure the student is registered in the database first."
        if self._acting_on_other_student():
            return "Permission denied: students can only cancel their own requests."

        if temp_id is None:
            temp_app_list = self._find_student_temp_apps()
            if len(temp_app_list) == 0:
                return f"no temporary appointment requests found for student '{student_name}'."
            if len(temp_app_list) > 1:
                return ("student has many temporary appointment requests. "
                        "Send this list back to the student and ask to clarify "
                        "with the temporary appointment's id number. "
                        f"\n{temp_app_list}")
            temp_id = temp_app_list[0][0]
        #the id must belong to this student, so nobody can remove another student's request by id
        if not self._find_temp_app(temp_id, self.student[0]):
            return f"temporary appointment {temp_id} not found for {student_name}."

        #read as strings: the id may be an int (from the model) or a str (from the lookup above)
        df = pd.read_csv(self._path(TEMP_APPS_CSV), dtype=str)
        remaining = df[df["temp_id"] != str(temp_id)]
        if len(remaining) == len(df):
            return f"temporary appointment {temp_id} could not be removed."
        remaining.to_csv(self._path(TEMP_APPS_CSV), index=False)
        if self.is_tutor():
            text = f"Your tutor canceled your reschedule request #{temp_id}."
        else:
            text = f"{self.user[PEOPLE_NAME]} has canceled their reschedule request #{temp_id}."
        self._queue(self._other_party(), text)
        return f"temporary appointment {temp_id} removed."


    def remove_appointment(self, student_name, day, app_id=None):
        if not self.is_tutor():
            return "Permission denied: only tutors can permanently remove appointments."
        if not self.find_student(student_name):
            return f"student \'{student_name}\' not found in database. Make sure the student is registered in the database first."

        if app_id is None:
            if not self._find_og_app(day, self.student[0]):
                app_list = self.return_student_app_list()
                return (f"{student_name}'s appointment on {day} was not found. "
                        "Send this list back to the tutor and ask to clarify "
                        "which appointment day and appointment ID they want to remove."
                        f"\n{app_list}")
        elif not self._find_og_app_with_id(app_id):
            return f"appointment {app_id} not found for {student_name}."

        removed_id = str(self.og_app[0])
        sched = pd.read_csv(self._path(SCHEDULE_CSV), dtype=str)
        sched[sched["app_id"] != removed_id].to_csv(self._path(SCHEDULE_CSV), index=False)

        #also drop temp rows (reschedule requests / cancellations) that pointed at the removed
        #appointment, otherwise they would linger as orphans and still show up in schedule views
        temp = pd.read_csv(self._path(TEMP_APPS_CSV), dtype=str)
        temp[temp["app_id"] != removed_id].to_csv(self._path(TEMP_APPS_CSV), index=False)
        start, end = self.convert_24_to_12h(self.og_app[3], self.og_app[4])
        self._queue(self.student, f"You no longer have an appointment on {self.og_app[2]} {start}-{end} with your tutor. Please consult them if you have any questions.")
        return f"appointment {removed_id} for {student_name} on {self.og_app[2]} permanently removed."


    #approve or deny schedule request
    def approve_appointment(self, student_name, approval, temp_id=None):
        if not self.is_tutor():
            return "Permission denied: only tutors can approve or deny requests."
        if not self.find_student(student_name):
            return f"student \'{student_name}\' not found in database. Make sure the student is registered in the database first."

        if temp_id is None:  # NOT `if not temp_id`: temp id 0 is valid
            temp_app_list = self._find_student_temp_apps()
            if len(temp_app_list) == 0:
                return f"no temporary appointment requests found for student '{student_name}'."
            if len(temp_app_list) > 1:
                return ("student has many temporary appointment requests. "
                        "Send this list back to the student and ask to clarify "
                        "with the temporary appointment's id number. "
                        f"\n{temp_app_list}")
            temp_id = temp_app_list[0][0]

        if not self._find_temp_app(temp_id, self.student[0]):
            return f"temporary appointment {temp_id} not found for {student_name}."

        # The agent sends a boolean; the CSV (and _is_active_temp) use 1 / 0.
        approval_value = 1 if approval in (True, 1, "1", "true", "True") else 0
        df = pd.read_csv(self._path(TEMP_APPS_CSV))
        df.loc[df['temp_id'] == int(temp_id), 'approval'] = approval_value
        df.to_csv(self._path(TEMP_APPS_CSV), index=False)
        approval_str = "approved!" if approval_value == 1 else "denied, please talk to your tutor."
        start, end = self.convert_24_to_12h(self.temp_app[4], self.temp_app[5])
        self._queue(self.student, f"Your reschedule request #{temp_id} ({self.temp_app[3]} {start}-{end}) was {approval_str}")
        return f"temporary appointment {temp_id} {'approved' if approval_value else 'denied'}"


    #-----------------------Adding new entries to database (Tutor Specific)----------------------------
    #Add new student to database
    def add_new_student(self, name, phone_num):
        df = pd.read_csv(self._path(PEOPLE_CSV))
        id = self._next_id(df)

        # Build the row using the column constants so it matches what
        # find_user / find_student read. Unknown columns are left empty.
        new_student = [""] * PEOPLE_NUM_COLS
        new_student[PEOPLE_ID] = id
        new_student[PEOPLE_PHONE] = phone_num
        new_student[PEOPLE_NAME] = name
        new_student[PEOPLE_ROLE] = "student"
        with open(self._path(PEOPLE_CSV), mode='a', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(new_student)
        return f"New student {name} added."

    #Add new appointment to database
    def add_new_app(self, student_name, day, start_time, end_time):
        if self.check_conflicts(day, start_time, end_time):
            return "conflicts with another appointment, select a different time."
        if not self.find_student(student_name):
            return f"student \'{student_name}\' not found in database. Make sure the student is registered in the database first."

        df = pd.read_csv(self._path(SCHEDULE_CSV))
        id = self._next_id(df)
        new_app = [id, self.student[0], day, start_time, end_time]
        with open(self._path(SCHEDULE_CSV), mode='a', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(new_app)

        ap_start, ap_end = self.convert_24_to_12h(start_time, end_time)
        return f"Appointment for {student_name} on {day}, {ap_start}-{ap_end} added."

    #convert 24 hour time to am/pm time for the azure agent.
    def convert_24_to_12h(self, start_str, end_str):
        obj_start = datetime.strptime(start_str, "%H:%M")
        obj_end = datetime.strptime(end_str, "%H:%M")
        return obj_start.strftime("%I:%M %p"), obj_end.strftime("%I:%M %p")

    #-------------------------------------Text Notifications------------------------------------------------------
    #Queue a text for `recipient` (a people-CSV row). Called by the tool methods ONLY after their write
    #succeeded. Nothing is sent here: foundry_module delivers self.notifications after the turn.
    def _queue(self, recipient, text):
        if recipient is None:
            return None
        if recipient[PEOPLE_ID] == self.user[PEOPLE_ID]:
            return None  #don't send notifications to the person you're already responding to.
        self.notifications.append((
            recipient[PEOPLE_ID],
            recipient[PEOPLE_PHONE],
            recipient[PEOPLE_NAME],
            recipient[PEOPLE_CONVO] if len(recipient) > PEOPLE_CONVO else "",
            text
        ))
        return True

    #who needs to hear about an action the sender took on self.student
    def _other_party(self):
        if self.is_tutor():
            return self.student
        return self.get_tutor()
