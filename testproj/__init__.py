from flask import Flask
from flaskext.mysql import MySQL
from mysql import connector
from mysql.connector import Error

app = Flask(__name__)
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = '9AYNdyF4xS$D6V'
app.config['MYSQL_DATABASE_DB'] = 'ksl-data'
app.config['MYSQL_DATABASE_HOST'] = 'sqluser'
mysql = MySQL(app)

try:
    connection = connector.connect(host='localhost', database='ksl-data',
         user='sqluser', password='9AYNdyF4xS$D6V')
    if connection.is_connected():
        db_Info = connection.get_server_info()
        print("Connected to MySQL Server version ", db_Info)
        cursor = connection.cursor()
        cursor.execute("select database();")
        record = cursor.fetchone()
        print("You're connected to database: ", record)
except Error as e:
    print("Error while connecting to MySQL, Error", e)