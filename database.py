import csv
import pandas as pd
import re
from datetime import datetime

class Database:
    def init(self):
        self.user
        self.og_app
        self.temp_app
        
    
    """
    reschedule: reschedule <og_day_int> <new_day_int> <start> <end>
    view appointments: view 
    
    Tutor specific:
    add student: add student <student name> <phone_number>
    add new appointment: add appointment <student_id> <day> <start_time> <end_time>
    view appointments for student: view <student_id>
    view appointments for day: view day
    view appointments for week: view all
    approve appointment request: request <approve>/<deny> <temp_id>
    """
    
    #decifer if tutor or student
    def read_message(self, message, phone_num):
        print(message)
        print(phone_num)
        with open('mock_people_database.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            
            #find user number in database
            for u in reader:
                if u[2] == phone_num:
                    self.user = u
                    break
        
        if self.user[3] == 'tutor':
            response = self.parse_tutor_message(message)
        else:
            response = self.parse_student_message(message)
        return response
    
    
    def parse_tutor_message(self, message):
        re_command = re.search(r'^(\w+)', message)
        str_command = re_command.group()
                
        if str_command == "add":
            response = self.add_command(message)
        elif str_command == "request":
            response = self.approve_appointment(message)
        elif str_command == "view":
                response = self.return_indie_app_list(message)
                
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
        re_ap_day = re.search(r'^w+\s(\d)', message)
        re_new_day = re.search(r'^w+\s\d\s(\d)', message)
        re_start = re.search(r'(\d+:\d+)\s\d+:\d+$', message)
        re_end = re.search(r'(\d+:\d+)$', message)
        ap_day = re_ap_day.group()
        new_day = re_new_day.group()
        new_start = re_start.group()
        new_end = re_end.group()
        
        if self._find_og_app(ap_day) == False:
            return "original appointment not found"
        conflict_check_result = self.check_conflicts(new_day, new_start, new_end)
        if conflict_check_result:
            return conflict_check_result
        return self.append_new_temp_app(ap_day, new_day, new_start, new_end)
        
        
    def check_conflicts(self, new_day, new_start, new_end):
        with open('mock_schedule.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[2] == new_day and (app[3] < new_end and app[4] > new_start):
                    return f"conflict with standard appointment {app[0]}"
        with open('mock_temp_apps.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
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
        with open('temp_apps.csv', mode='r', encoding='utf-8') as file:
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
        with open('mock_temp_apps.csv', mode='a', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(new_temp_app)
            
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
    def process_view(self, message):
        re_command = re.search(r'^w+\s(\w+)', message)
        if not re_command:
            return self.return_indie_app_list(self.user)
        command = re_command.group()
        
        if command == "all":
            return self.return_complete_app_list()
        elif command == "day":
            return self.return_day_list()
        else:
            return self.return_indie_app_list(command)
        
    
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
        re_command = re.search(r'^w+\s(\w+)', message)
        command = re_command.group()
        
        if command == "student":
            re_name = re.search(r'(w+)$', message)
            re_number = re.search(r'(w+)$', message)
            name = re_name.group()
            number = re_number.group()
            
            df = pd.read_csv('mock_people_database.csv')
            if df.shape[0] == 0:
                id = 0
            else:
                id = df.shape[0] + 1
            new_student = [id, name, number]
            with open('mock_people_database.csv', mode='a', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerows(new_student)
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
            with open('mock_schedule.csv.csv', mode='a', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerows(new_app)
            response = new_app
        return response
        
    #approve or deny schedule request
    def approve_appointment(self, message):
        re_approval = re.search(r'request (w+)', message)
        re_temp_id = re.search(r'(\d+)$', message)
        approval = re_approval.group()
        temp_id = int(re_temp_id.group())
        
        if self._find_temp_app(temp_id):
            df = pd.read_csv('mock_temp_apps.csv')
            df.loc[df['temp_id'] == temp_id, 'approval'] = approval
            return f"temporary appointment {temp_id} approved"
        return f"temporary appointment {temp_id} denied"