from __init__  import db
from flask_login import UserMixin

# Employee Model
class Employees(db.Model, UserMixin):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    email = db.Column(db.String)
    password = db.Column(db.String)
    address = db.Column(db.String)
    phone = db.Column(db.String)
    is_hr = db.Column(db.Integer) # 0 for not in HR, 1 for in HR
    supv = db.Column(db.String)
    is_supv = db.Column(db.Integer) # 0 for not a supervisor, 1 for supervisor

    def __init__(self, name, email, password, 
        address, phone, is_hr, supv, is_supv, is_active):
        self.name = name
        self.email = email
        self.password = password
        self.address = address
        self.phone = phone
        self.is_hr = is_hr
        self.supv = supv
        self.is_supv = is_supv
    
    def get_id(self):
        return self.id

# Timesheet Model
class Timesheet(db.Model):
    __tablename__ = "timesheet"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    date = db.Column(db.String)
    time_enter = db.Column(db.String)
    time_leave = db.Column(db.String)
    pto = db.Column(db.Float)
    hours = db.Column(db.Float)
    approval = db.Column(db.String)

    def __init__(self, name, date, time_enter, time_leave, pto, hours, approval):
        self.name = name
        self.date = date
        self.hours = hours
        self.time_enter = time_enter
        self.time_leave = time_leave
        self.pto = pto
        self.approval = approval