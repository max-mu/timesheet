from flask import Flask
from flaskext.mysql import MySQL
from mysql import connector
from mysql.connector import Error

app = Flask(__name__)
app.config['MYSQL_DATABASE_USER'] = 'user'
app.config['MYSQL_DATABASE_PASSWORD'] = 'nmg130-Nv'
app.config['MYSQL_DATABASE_DB'] = 'ksl-data'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql = MySQL(app)

# try:
connection = connector.connect(host='localhost', database='ksl-data',
        user='user', password='nmg130-Nv')
if connection.is_connected():
    db_Info = connection.get_server_info()
    print("Connected to MySQL Server version ", db_Info)
    cursor = connection.cursor()
    cursor.execute("select database();")
    record = cursor.fetchone()
    print("You're connected to database: ", record)
# except Error as e:
#     print("Error while connecting to MySQL, Error", e)