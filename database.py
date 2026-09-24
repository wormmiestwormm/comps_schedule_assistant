import csv
import pandas as pd
import re
from datetime import datetime

class Database:
    def init(self):
        self.phone_num
        self.user
        self.og_app
        self.temp_app
    
    #decifer if tutor or student
    def find_user(self, phone_num):
        print("attempting to find user")
        print(phone_num)
        with open('mock_people_database.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            
            #find user number in database
            for u in reader:
                if u[2] == phone_num:
                    print(f"user is: {u[3]}")
                    self.phone_num = phone_num
                    self.user = u
                    return True
        print(f"user {phone_num} not found")
        return False


    #find student in database by name
    def find_student(self, name):
        print(f"finding {name} in mock_people_database")
        with open('mock_people_database.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            
            #find user number in database
            for s in reader:
                if name in s[2]:
                    print(f"student found: {u}")
                    return s
        
        return "name not in database"
    
    
    def parse_tutor_message(self, message):
        re_command = re.search(r'^(\w+)', message)
        str_command = re_command.group(1)
                
        if str_command == "add":
            print("add command")
            response = self.add_command(message)
        elif str_command == "request":
            print("request command")
            response = self.approve_appointment(message)
        elif str_command == "view":
            print("view command")
            response = self.process_view(message)
        else:
            print("missed command")
        return response
        
    def parse_student_message(self, message):
        re_command = re.search(r'^(\w+)', message)
        str_command = re_command.group()
        
        if str_command == "reschedule":
            response = self.process_reschedule(message)
            if not response:
                response = self.append_new_temp_app(message)
        else: #str_command == "view"
            response = self.process_view(message)
        
        return response
    
    
    #check for conflicts with standard schedule AND any existing temp appointments
    def process_reschedule(self, message):
        parts = message.strip().split()

        if len(parts) == 4:
            ap_day = parts[1]
            new_day = parts[1]
            new_start = parts[2]
            new_end = parts[3]
        elif len(parts) == 5:
            ap_day = parts[1]
            new_day = parts[2]
            new_start = parts[3]
            new_end = parts[4]
        else:
            return "invalid reschedule format"

        if not re.fullmatch(r'\d+', ap_day):
            return "invalid appointment day"

        if self._find_og_app(ap_day) == False:
            return "original appointment not found"
        conflict_check_result = self.check_conflicts(new_day, new_start, new_end)
        if conflict_check_result:
            return conflict_check_result
        return self.append_new_temp_app(new_day, new_start, new_end)
        
        
    def check_conflicts(self, new_day, new_start, new_end):
        og_app_id = self.og_app[0] if self.og_app else None

        with open('mock_schedule.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[0] == og_app_id:
                    continue
                if app[2] == new_day and (app[3] < new_end and app[4] > new_start):
                    return f"conflict with standard appointment {app[0]}"
        with open('mock_temp_apps.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[1] == og_app_id:
                    continue
                if app[3] == new_day and (app[4] < new_end and app[5] > new_start):
                    return f"conflict with standard appointment {app[0]}"
    
    
    #verify that original appointment exists
    def _find_og_app(self, ap_day):
        with open('mock_schedule.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[1] == self.user[0] and app[2] == ap_day:
                    self.og_app = app
                    return True
        return False
    
    #verify that temporary appointment exists
    def _find_temp_app(self, temp_id):
        with open('mock_temp_apps.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[0] == temp_id:
                    self.temp_app = app
                    return True
        return False
    
    
    #append new temp reschedule
    def append_new_temp_app(self, new_day, new_start, new_end):
        df = pd.read_csv('mock_temp_apps.csv')
        if df.shape[0] == 0:
            id = 0
        else:
            id = df.shape[0] + 1
        new_temp_app = [id, self.og_app[0], self.user[0], new_day, new_start, new_end, 0, 0]
        print(f"new_temp_app: {new_temp_app}")
        with open('mock_temp_apps.csv', mode='a', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(new_temp_app)

        #will also return message for the tutor, requires second phone number though
        return f"Appointment for {self.og_app[0]} changed to {new_day}, {new_start} - {new_end}"
    
    
    #returns app or temp app for user
    def return_indie_app_list(self, person):
        return_list = []
        og_app_ids = []
        with open('mock_temp_apps.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[2] == person[0] and app[6] == 1 and app[7] == 0:
                    return_list.append(app)
                    og_app_ids.append(app[1])
        with open('mock_schedule.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[1] == person[0] and app[0] not in og_app_ids:
                    return_list.append(app)
        return return_list
        
    
    #----------------------tutor specific interactions----------------------
    #these require a 3rd phone number
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
            student = self.find_student(student_name)
            return self.return_indie_app_list(student)
        else:
            return "Error: specificity argument was not one of the established values, please try again."
        
    
    def return_complete_app_list(self):
        return_list = []
        og_app_ids = []
        with open('mock_temp_apps.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[6] == 1 and app[7] == 0:
                    return_list.append(app)
                    og_app_ids.append(app[1])
        with open('mock_schedule.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[0] not in og_app_ids:
                    return_list.append(app)
        return return_list
        
        
    def return_day_list(self):
        curr_day = datetime.now().isoweekday()
        return_list = []
        og_app_ids = []
        with open('mock_temp_apps.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[3] == curr_day and (app[6] == 1 and app[7] == 0):
                    return_list.append(app)
                    og_app_ids.append(app[1])
        with open('mock_schedule.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[3] == curr_day and app[0] not in og_app_ids:
                    return_list.append(app)
        return return_list
        
        
    def add_command(self, message):
        re_command = re.search(r'^\w+\s(\w+)', message)
        command = re_command.group()
        
        if command == "student":
            re_name = re.search(r'(\w+)$', message)
            re_number = re.search(r'(\w+)$', message)
            name = re_name.group()
            number = re_number.group()
            
            df = pd.read_csv('mock_people_database.csv')
            if df.shape[0] == 0:
                id = 0
            else:
                id = df.shape[0] + 1
            new_student = [id, name, number]
            with open('mock_people_database.csv', mode='a', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(new_student)
            response = new_student
        elif command == "appointment":
            re_student_id = re.search(r'^add appointment (\d+)', message)
            re_day = re.search(r'^add appointment \d+ (\d)', message)
            re_start = re.search(r'(\d+:\d+)\s\d+:\d+$', message)
            re_end = re.search(r'(\d+:\d+)$', message)
            student_id = re_student_id.group()
            day = re_day.group()
            start = re_start.group()
            end = re_end.group()
                        
            df = pd.read_csv('mock_schedule.csv')
            if df.shape[0] == 0:
                id = 0
            else:
                id = df.shape[0] + 1
            new_app = [id, student_id, day, start, end]
            with open('mock_schedule.csv', mode='a', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(new_app)
            response = new_app
        return response
        
    #approve or deny schedule request
    def approve_appointment(self, message):
        re_approval = re.search(r'^request (\w+)', message)
        re_temp_id = re.search(r'(\d+)$', message)

        if not re_approval or not re_temp_id:
            return "invalid request format"

        approval_text = re_approval.group(1).lower()
        if approval_text not in {'approve', 'deny'}:
            return "invalid approval value"

        approval = 1 if approval_text == 'approve' else 0
        temp_id = re_temp_id.group()

        if self._find_temp_app(temp_id):
            df = pd.read_csv('mock_temp_apps.csv')
            df.loc[df['temp_id'] == int(temp_id), 'approval'] = approval
            df.to_csv('mock_temp_apps.csv', index=False)
            return f"temporary appointment {temp_id} {approval_text}"
        else:
            return f"temporary appointment {temp_id} not found"