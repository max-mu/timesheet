from flask import Flask
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from mysql import connector
from mysql.connector import Error
from flaskext.mysql import MySQL

app = Flask(__name__)
# TODO: Change this key in the end
app.config['SECRET_KEY'] = 'not a secure key'    
Bootstrap(app)
# SQLite
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timesheet.db'
# MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:9AYNdyF4xS$D6V@localhost/ksl-data'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

from models import Employees
login_manager = LoginManager(app)

@login_manager.user_loader
def load_user(user_id):
    return Employees.query.get(user_id)

'''
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = '9AYNdyF4xS$D6V'
app.config['MYSQL_DATABASE_DB'] = 'ksl-data'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql = MySQL(app)
'''
'''
try:
    connection = connector.connect(host='127.0.0.1', database='ksl-data',
         user='root', password='9AYNdyF4xS$D6V')
    if connection.is_connected():
        db_Info = connection.get_server_info()
        print("Connected to MySQL Server version ", db_Info)
        cursor = connection.cursor()
        cursor.execute("select database();")
        record = cursor.fetchone()
        print("You're connected to database: ", record)
except Error as e:
    print("Error while connecting to MySQL", e)
'''