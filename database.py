import csv
import pandas as pd
import re

class Database:
    def init(self):
        self.user
        self.og_app
        self.temp_app
        
    
    """
    reschedule: reschedule <og_day_int> <new_day_int> <start> <end>
    app request: view
    schedule request: 
    """
    
    #decifer if A) tutor or student, and B) if reschedule request or info request
    def read_message(self, message, phone_num):
        with open('mock_people_database.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            
            #find user number in database
            for u in reader:
                if u[2] == phone_num:
                    self.user = u
                    break
        re_command = re.search(r'^(\w+)', message)
        str_command = re_command.group()
        
        if str_command == "reschedule":
            response = self.process_reschedule(message)
            if not response:
                response = self.append_new_temp_app(message)
        elif str_command == "view":
            response = self.return_app_list(message)
        
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
    
    
    #append new temp reschedule
    def append_new_temp_app(self, new_day, new_start, new_end):
        df = pd.read_csv('data.csv')
        if df.shape[0] == 0:
            id = 0
        else:
            id = df.shape[0] + 1
        new_temp_app = [id, self.og_app[0], self.user[0], new_day, new_start, new_end, 0]
        with open('mock_temp_apps.csv', mode='a', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerows(new_temp_app)
        return f"Appointment for {self.og_app[0]} changed to {new_day}, {new_start} - {new_end}"
    
    #returns app or temp app for user
    def return_app_list(self):
        return_list = []
        i = 0
        with open('mock_schedule.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[1] == self.user[0]:
                    return_list[i] = app
                    i += 1
        with open('mock_temp_apps.csv', mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            for app in reader:
                if app[2] == self.user[0]:
                    return_list[i] = app
                    i += 1
        return return_list
        
    
    #----------------------tutor specific interactions----------------------
    #these require a 3rd phone number
    
    #approve or deny schedule request
    def approve_appointment(self):
        pass
    
    #returns schedule for the day
    def return_day_schedule(self):
        pass