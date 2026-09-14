import csv

class Database:
    def init(self):
        pass
    
    #decifer if A) tutor or student, and B) if reschedule request or info request
    def read_message(self):
        pass
    
    #check for conflicts with standard schedule AND any existing temp appointments
    def check_app_conflicts(self):
        pass
    
    #adds temp reschedule
    def reschedule_app(self):
        pass
    
    #returns app or temp app for user
    def return_app_list(self):
        pass
    
    #----------------------tutor specific interactions----------------------
    #these require a 3rd phone number
    
    #approve or deny schedule request
    def approve_appointment(self):
        pass
    
    #returns schedule for the day
    def return_day_schedule(self):
        pass