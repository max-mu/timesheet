#!bin/python
from flask import Flask, request, render_template, redirect, url_for
from forms import LoginForm, HoursForm
from flask_bootstrap import Bootstrap

app = Flask(__name__)
app.config['SECRET_KEY'] = 'not a secure key'
Bootstrap(app)

@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate_on_submit():
        return redirect( url_for('hours'))
    return render_template('login.html', form=form)

@app.route('/hours', methods=['GET', 'POST'])
def hours():
    form = HoursForm(request.form)
    if request.method == 'POST' and form.validate_on_submit():
        return 'Your hours have been submitted!'
    return render_template('hours.html', form=form)

if __name__ == '__main__':
    app.run()