from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(_name_)
app.config['SECRET_KEY'] = 'your_enterprise_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///enterprise_logs.db'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

socketio = SocketIO(app)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class LogEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(500), nullable=False)
    level = db.Column(db.String(50), nullable=False) # INFO, ERROR, WARNING
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

with app.app_context():
    db.create_all()

# Routes
@app.route('/')
@login_required
def index():
    logs = LogEntry.query.order_by(LogEntry.timestamp.desc()).all()
    return render_template('index.html', logs=logs)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        hashed_password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        new_user = User(username=request.form['username'], password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/add_log', methods=['POST'])
@login_required
def add_log():
    message = request.form.get('message')
    level = request.form.get('level', 'INFO')
    if message:
        new_log = LogEntry(message=message, level=level)
        db.session.add(new_log)
        db.session.commit()
        
        # Real-time broadcast using WebSockets
        socketio.emit('new_log', {'message': message, 'level': level, 'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')})
    return redirect(url_for('index'))

if _name_ == '_main_':
    socketio.run(app, debug=True, port=5000)