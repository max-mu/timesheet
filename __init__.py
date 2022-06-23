from flask import Flask
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_principal import Principal
from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)
# TODO: Change this key in the end
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
Bootstrap(app)

user = os.getenv('DB_USER')
password = os.getenv('DB_PASSWORD')
host = os.getenv('DB_HOST')
database = os.getenv('DB_NAME')

# SQLAlchemy is used for login authorization
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///%s'%(database)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
db = SQLAlchemy(app)

from models import Employees
login_manager = LoginManager(app)

@login_manager.user_loader
def load_user(user_id):
    return Employees.query.get(user_id)

# All other queries are done through MySQL

Principal(app)
