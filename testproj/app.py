from flask_mysqldb import MySQL
from flask import Flask


app = Flask(__name__)
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Test1234!'
app.config['MYSQL_DB'] = 'ksldata'
app.config['MYSQL_HOST'] = '127.0.0.1'
mysql = MySQL(app)

# Default route
@app.route('/', methods=['GET', 'POST'])
def index():
    cur = mysql.connection.cursor()
    return 'Index'

if __name__ == '__main__':
    app.run()