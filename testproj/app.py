from __init__ import app

# Default route
@app.route('/')
def index():
    return 'Index'

if __name__ == '__main__':
    app.run()