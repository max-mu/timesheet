from __init__  import db
from flask_login import UserMixin

# Employee Model
class Employees(UserMixin, db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    email = db.Column(db.String)
    password = db.Column(db.String)
    address = db.Column(db.String)
    phone = db.Column(db.String)
    is_hr = db.Column(db.Integer) # 0 for not in HR, 1 for in HR
    supervisor = db.Column(db.String)
    is_supervisor = db.Column(db.Integer) # 0 for not a supervisor, 1 for supervisor

    def get_id(self):
        return self.id

# Timesheet Model
class Timesheet(db.Model):
    __tablename__ = "timesheet"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    hours = db.Column(db.Float)
    date = db.Column(db.String)
    approval = db.Column(db.String)

    def __init__(self, name, hours, date, approval):
        self.name = name
        self.hours = hours
        self.date = date
        self.approval = approval