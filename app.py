from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
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
    ip_address = db.Column(db.String(50), default="127.0.0.1") # Server IP address
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
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid username or password, please try again.')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose another.')
            return redirect(url_for('signup'))
            
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! Please login.')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/add_log', methods=['POST'])
def add_log():
    message = request.form.get('message')
    level = request.form.get('level', 'INFO')
    
    # Identifying the actual IP address of the log-sending agent
    ip_address = request.headers.get('X-Forwarded-For', request.remote_addr) or "127.0.0.1"
    
    if message:
        new_log = LogEntry(message=message, level=level, ip_address=ip_address)
        db.session.add(new_log)
        db.session.commit()
        
        formatted_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        # Sending to all clients via WebSocket, including the IP address
        socketio.emit('new_log', {
            'message': message, 
            'level': level, 
            'ip_address': ip_address,
            'timestamp': formatted_time
        })
    return "Log received", 200

@app.route('/clear_logs', methods=['POST'])
@login_required
def clear_logs():
    LogEntry.query.delete()
    db.session.commit()
    flash('All logs cleared successfully.')
    return redirect(url_for('index'))

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
