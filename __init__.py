from flask import Flask
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flaskext.mysql import MySQL
from flask_principal import Principal
from decouple import config

app = Flask(__name__)
# TODO: Change this key in the end
app.config['SECRET_KEY'] = config('SECRET_KEY')
Bootstrap(app)

user = config('DB_USER')
password = config('DB_PASSWORD')
host = config('DB_HOST')
database = config('DB_NAME')

# SQLAlchemy is used for login authorization
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://%s:%s@%s/%s'%(user, 
    password, host, database)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

from models import Employees
login_manager = LoginManager(app)

@login_manager.user_loader
def load_user(user_id):
    return Employees.query.get(user_id)

# All other queries are done through MySQL
app.config['MYSQL_DATABASE_USER'] = user
app.config['MYSQL_DATABASE_PASSWORD'] = password
app.config['MYSQL_DATABASE_DB'] = database
app.config['MYSQL_DATABASE_HOST'] = host
mysql = MySQL(app)

Principal(app)