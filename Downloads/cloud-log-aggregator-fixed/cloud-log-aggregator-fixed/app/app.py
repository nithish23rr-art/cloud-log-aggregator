"""M&K Nexus Cloud - app.py (all 6 fixes applied)
Assumed module file names (rename the imports if yours differ):
  compliance.py      -> compliance_bp, generate_csv_report
  otp_utils.py       -> send_developer_otp, verify_developer_otp
  alert_gateway.py   -> alert_gateway_bp
  log_hub.py         -> log_hub_bp
  enterprise.py      -> enterprise_bp, register_socket_events
"""
import os
from datetime import datetime
from flask import (Flask, render_template, request, redirect, url_for,
                   flash, session)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, login_required,
                         logout_user, current_user)
from flask_socketio import SocketIO, emit
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash 
from dotenv import load_dotenv
load_dotenv()

# FIX 2/3/4: blueprint + socket imports

from compliance import compliance_bp
from alert_gateway import alert_gateway_bp
from log_hup import log_hub_bp
from enterprise import enterprise_bp, register_socket_events
from otp_utils import send_developer_otp, verify_developer_otp

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
# static/ sits next to app/ (project root), so point Flask at it explicitly
_static = os.path.join(BASE_DIR, 'static')
if not os.path.isdir(_static):
    _static = os.path.join(BASE_DIR, '..', 'static')
app = Flask(__name__, static_folder=os.path.abspath(_static))
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'mk-nexus-fallback-key-dev-only')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'mknexus_ultimate.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = True

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')
csrf = CSRFProtect(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='Admin')

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    level = db.Column(db.String(20), nullable=False)
    message = db.Column(db.String(1000), nullable=False)
    tag = db.Column(db.String(50), nullable=False)
    trace_id = db.Column(db.String(50), nullable=True)
    sentiment = db.Column(db.String(20), nullable=True, default='Neutral')
    threat_score = db.Column(db.Float, nullable=True, default=0.01)


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


# ---------- Blueprints ----------
# FIX 2: register all blueprints.
app.register_blueprint(compliance_bp)      # CSRF stays ON: the dashboard sends X-CSRFToken
app.register_blueprint(alert_gateway_bp)
app.register_blueprint(log_hub_bp)
app.register_blueprint(enterprise_bp)

# FIX 3: API-key endpoints are called by external clients (no browser CSRF token).
# They are protected by the X-API-Key header instead.
csrf.exempt(alert_gateway_bp)
csrf.exempt(log_hub_bp)
csrf.exempt(enterprise_bp)

# FIX 4: live telemetry socket events (subscribe_live_logs / new_live_log)
register_socket_events(socketio)


# ---------- Pages ----------
@app.route('/intro')
def introduction():
    """Public landing page."""
    return render_template('introduction.html')


@app.route('/')
@login_required
def index():
    try:
        logs = Log.query.order_by(Log.timestamp.desc()).limit(150).all()
        return render_template('index.html', logs=logs, current_user=current_user)
    except Exception as exc:
        flash(f'Error loading logs: {exc}', 'danger')
        return render_template('index.html', logs=[], current_user=current_user)


@app.route('/add_log', methods=['POST'])
@login_required
def add_log():
    try:
        message = (request.form.get('message') or '').strip()
        level = (request.form.get('level') or 'INFO').strip()
        tag = (request.form.get('tag') or 'Python-Core').strip()

        if not message:
            flash('Log message cannot be empty.', 'warning')
            return redirect(url_for('index'))

        safe_message = message.replace('password=', 'password=*').replace('api_key=', 'api_key=*')
        trace_id = f"#MK-TRC-{datetime.utcnow().strftime('%H%M%S%f')[:8]}"
        threat = 0.98 if level == 'ERROR' else 0.01
        sentiment = 'Critical' if level == 'ERROR' else 'Neutral'

        new_log = Log(message=safe_message, level=level, tag=tag,
                      trace_id=trace_id, threat_score=threat, sentiment=sentiment)
        db.session.add(new_log)
        db.session.commit()

        # FIX 5: no broadcast=True (removed in newer Flask-SocketIO;
        # socketio.emit already goes to every connected client).
        socketio.emit('new_log', {
            'timestamp': new_log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'level': new_log.level,
            'tag': new_log.tag,
            'message': new_log.message,
            'trace_id': new_log.trace_id,
        })
        flash('Secure log successfully ingested into Quantum Vault!', 'success')
    except Exception as exc:
        db.session.rollback()
        flash(f'Error adding log: {exc}', 'danger')
    return redirect(url_for('index'))


# FIX 6: the terminal is a Socket.IO event (not an HTTP route) - the dashboard uses socket.emit.
@socketio.on('terminal_command')
def handle_terminal_command(data):
    try:
        if isinstance(data, dict):
            cmd = str(data.get('command', '') or '').strip()
        elif isinstance(data, str):
            cmd = data.strip()
        else:
            cmd = ''

        response_msg = f'>> {cmd}\n'
        if cmd == 'help':
            response_msg += 'Available commands: status, mesh-check, clear, version\n'
        elif cmd == 'status':
            response_msg += 'M&K Nexus Cloud Core: ONLINE\nActive Clusters: Mumbai, London, Singapore\n'
        elif cmd == 'mesh-check':
            response_msg += 'Cross-Cluster Latency: 14ms. Zero-Trust Vault: SECURE.\n'
        elif cmd == 'version':
            response_msg += 'M&K Enterprise Intelligence Terminal v15.0\n'
        elif cmd == 'clear':
            response_msg += 'CLEAR'
        else:
            response_msg += f"Command not recognized: {cmd}. Type 'help' for options.\n"
        emit('terminal_response', {'output': response_msg})
    except Exception as exc:
        emit('terminal_response', {'output': f'Error processing command: {exc}\n'})




@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            username = (request.form.get('username') or '').strip()
            email = (request.form.get('email') or '').strip().lower()
            password = request.form.get('password') or ''
            role = (request.form.get('role') or 'Admin').strip()

            if not username or not password or not email:
                flash('All fields are required.', 'warning')
                return render_template('signup.html')
            
            if len(username) < 3:
                flash('Username must be at least 3 characters.', 'warning')
                return render_template('signup.html')
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists. Please choose another.', 'warning')
                return redirect(url_for('signup'))
            if User.query.filter_by(email=email).first():
                flash('Email already registered. Please use another.', 'warning')
                return redirect(url_for('signup'))

            new_user = User(username=username, email=email, role=role)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            flash('Account created successfully! Please sign in.', 'success')
            return redirect(url_for('login'))
        except Exception as exc:
            db.session.rollback()
            flash(f'Signup error: {exc}', 'danger')
    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            username = (request.form.get('username') or '').strip()
            password = request.form.get('password') or ''
            if not username or not password:
                flash('Username and password are required.', 'warning')
                return render_template('login.html')

            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session['login_user_id'] = user.id
                session['otp_email'] = (user.email or '').strip().lower()

                ok, info = send_developer_otp(user.email)
                if not ok:
                    app.logger.error('Login OTP dispatch failed: %s', info)
                    flash('Could not send OTP right now. Please try again.', 'danger')
                    return render_template('login.html')

                flash('Password verified. Enter the 6-digit OTP sent to your email.', 'info')
                return redirect(url_for('verify_otp'))

            flash('Invalid username or password. Please try again.', 'danger')
        except Exception as exc:
            flash(f'Login error: {exc}', 'danger')
    return render_template('login.html')


# ---------- OTP + password recovery ----------
# Only these emails may receive a recovery OTP (comma separated in the environment).
# Without this, anyone could enter their own email, pass OTP, and reset any account.
ALLOWED_RESET_EMAILS = {e.strip().lower() for e in os.getenv('DEVELOPER_EMAILS', '').split(',') if e.strip()}


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        if email and email in ALLOWED_RESET_EMAILS:
            ok, info = send_developer_otp(email)
            if not ok:
                app.logger.error('OTP dispatch failed: %s', info)
        session['otp_email'] = email
        session.pop('login_user_id', None)
        flash('If this email is authorised, a verification code was sent.', 'info')
        return redirect(url_for('verify_otp'))
    return render_template('forgot_password.html')

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    email = session.get('otp_email') or (request.form.get('email') or '').strip().lower()
    if not email:
        flash('Start from the login or password recovery page.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        otp = (request.form.get('otp') or '').strip()

        # 1. Login OTP flow
        if session.get('login_user_id'):
            if verify_developer_otp(email, otp):
                user_id = session.pop('login_user_id', None)
                session.pop('otp_email', None)
                user = db.session.get(User, user_id)
                if user:
                    login_user(user)
                    flash('Successfully logged into M&K Nexus Cloud!', 'success')
                    return redirect(url_for('index'))
            flash('Invalid or expired code.', 'danger')

        # 2. Forgot password OTP flow
        elif email in ALLOWED_RESET_EMAILS:
            if verify_developer_otp(email, otp):
                session.pop('otp_email', None)
                session['dev_verified'] = True
                session['reset_verified'] = True
                flash('Verified. Set a new password.', 'success')
                return redirect(url_for('reset_password'))
            flash('Invalid or expired code.', 'danger')
        else:
            flash('Unauthorized email or invalid session.', 'danger')
            return redirect(url_for('login'))

    return render_template('verify_otp.html', email=email)


@app.route('/resend_otp', methods=['POST'])
def resend_otp():
    email = session.get('otp_email') or (request.form.get('email') or '').strip().lower()
    if email and (session.get('login_user_id') or email in ALLOWED_RESET_EMAILS):
        ok, info = send_developer_otp(email)
        if not ok:
            app.logger.error('OTP resend failed: %s', info)
    flash('If this email is authorised, a new code was sent.', 'info')
    return redirect(url_for('verify_otp'))


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if not session.get('reset_verified'):          # must pass OTP first
        flash('Verify your code before resetting a password.', 'warning')
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        confirm = request.form.get('confirm') or ''
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'warning')
        elif password != confirm:
            flash('Passwords do not match.', 'warning')
        else:
            user = User.query.filter_by(username=username).first()
            if not user:
                flash('No account with that username.', 'danger')
            else:
                try:
                    user.set_password(password)
                    db.session.commit()
                    session.pop('reset_verified', None)  
                    session.pop('dev_verified', None)  # one reset per verification
                    flash('Password updated. Please sign in.', 'success')
                    return redirect(url_for('login'))
                except Exception as exc:
                    db.session.rollback()
                    app.logger.error('Reset failed: %s', exc)
                    flash('Could not update the password. Try again.', 'danger')
    return render_template('reset_password.html')

@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))


# ---------- Errors ----------
@app.errorhandler(404)
def not_found(_error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(_error):
    return render_template('500.html'), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=False, host='0.0.0.0', port=5000)