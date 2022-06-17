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
    supv = db.Column(db.String)
    roles = db.Column(db.String)

    def __init__(self, name, email, password, 
        address, phone, supv, roles):
        self.name = name
        self.email = email
        self.password = password
        self.address = address
        self.phone = phone
        self.supv = supv
        self.roles = roles
    
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