from flask import Flask
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mysqldb import MySQL

app = Flask(__name__)
# TODO: Change this key in the end
app.config['SECRET_KEY'] = 'not a secure key'    
Bootstrap(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Test1234!@127.0.0.1/ksldata'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

from models import Employees
login_manager = LoginManager(app)

@login_manager.user_loader
def load_user(user_id):
    return Employees.query.get(user_id)

app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Test1234!'
app.config['MYSQL_DB'] = 'ksldata'
app.config['MYSQL_HOST'] = '127.0.0.1'
mysql = MySQL(app)