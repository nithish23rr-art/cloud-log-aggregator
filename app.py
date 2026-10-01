from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config["SECRET_KEY"] = "mk-nexus-ultimate-enterprise-secret-2026"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mknexus_ultimate.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# User Model with Authentication & RBAC
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), nullable=False, default="Admin")  # Admin / SRE / Developer


# Quantum Immutable Log Model
class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    level = db.Column(db.String(20), nullable=False)  # INFO, WARNING, ERROR
    message = db.Column(db.String(1000), nullable=False)
    tag = db.Column(db.String(50), nullable=False)
    trace_id = db.Column(db.String(50), nullable=True)
    sentiment = db.Column(db.String(20), nullable=True, default="Neutral")
    threat_score = db.Column(db.Float, nullable=True, default=0.01)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route("/")
@login_required
def index():
    logs = Log.query.order_by(Log.timestamp.desc()).limit(150).all()
    return render_template("index.html", logs=logs)


@app.route("/add_log", methods=["POST"])
@login_required
def add_log():
    message = (request.form.get("message") or "").strip()
    level = (request.form.get("level") or "INFO").upper()
    tag = (request.form.get("tag") or "Python-Core").strip()

    if not message:
        flash("Log message cannot be empty.", "warning")
        return redirect(url_for("index"))

    safe_message = message.replace("password=", "password=**").replace("api_key=", "api_key=**")
    trace_id = f"#MK-TRC-{datetime.utcnow().strftime('%H%M%S%f')[:8]}"

    threat = 0.98 if level == "ERROR" else 0.01
    sentiment = "Critical" if level == "ERROR" else "Neutral"

    new_log = Log(
        message=safe_message,
        level=level,
        tag=tag,
        trace_id=trace_id,
        threat_score=threat,
        sentiment=sentiment,
    )
    db.session.add(new_log)
    db.session.commit()

    socketio.emit(
        "new_log",
        {
            "timestamp": new_log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "level": new_log.level,
            "tag": new_log.tag,
            "message": new_log.message,
            "trace_id": new_log.trace_id,
            "threat_score": new_log.threat_score,
        },
    )

    flash("Secure log successfully ingested into Quantum Vault!", "success")
    return redirect(url_for("index"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            login_user(user)
            flash("Successfully logged into M&K Nexus Cloud!", "success")
            return redirect(url_for("index"))

        flash("Invalid username or password. Please try again.", "danger")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not username or not password:
            flash("Username and password are required.", "warning")
            return redirect(url_for("signup"))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists. Please choose another.", "warning")
            return redirect(url_for("signup"))

        new_user = User(username=username, password=password, role="Admin")
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please sign in.", "success")
        return redirect(url_for("login"))

    return render_template("signup.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out securely.", "info")
    return redirect(url_for("login"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)
