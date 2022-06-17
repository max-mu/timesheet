from flask import Flask
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flaskext.mysql import MySQL
from flask_principal import Principal

app = Flask(__name__)
# TODO: Change this key in the end
app.config['SECRET_KEY'] = 'not a secure key'    
Bootstrap(app)

# SQLAlchemy is used for login authorization
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Test1234!@127.0.0.1/ksldata'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

from models import Employees
login_manager = LoginManager(app)

@login_manager.user_loader
def load_user(user_id):
    return Employees.query.get(user_id)

# All other queries are done through MySQL
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'Test1234!'
app.config['MYSQL_DATABASE_DB'] = 'ksldata'
app.config['MYSQL_DATABASE_HOST'] = '127.0.0.1'
mysql = MySQL(app)

Principal(app)