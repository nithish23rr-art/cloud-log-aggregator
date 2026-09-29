from flask import Flask, render_template, request, redirect, url_for
import os

app = Flask(_name_)
LOG_FILE = "logs/app_activity.log"

@app.route('/')
def index():
    logs = []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            logs = f.readlines()
    return render_template('index.html', logs=logs)

@app.route('/add-log', methods=['POST'])
def add_log():
    log_msg = request.form.get('message')
    if log_msg:
        with open(LOG_FILE, "a") as f:
            f.write(f"{log_msg}\n")
    return redirect(url_for('index'))

if "_name_" == '_main_':
    app.run(debug=True, port=5000)
