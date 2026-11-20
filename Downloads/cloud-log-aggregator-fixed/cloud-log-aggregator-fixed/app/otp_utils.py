"""M&K Nexus Cloud - Developer OTP utility (hardened).
Same function names/returns as before, so app.py needs no change.
- secrets (cryptographically secure) instead of random
- 5 minute expiry, 5 wrong attempts then the code is burned
- 30 second resend cooldown
- constant-time comparison
Note: the store is in memory, so it works for one server process and resets on restart.
Use Redis or a database table if you run several workers.
"""
import os
import secrets
import smtplib
import hmac
import time
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

OTP_TTL_SECONDS = 300
MAX_ATTEMPTS = 5
RESEND_COOLDOWN = 30

DEVELOPER_OTP_STORE = {}   # email -> {"otp", "expires", "attempts", "sent_at"}
_lock = threading.Lock()


def send_developer_otp(developer_email):
    developer_email = (developer_email or "").strip().lower()
    sender_email = os.getenv("MAIL_USERNAME")
    sender_password = os.getenv("MAIL_PASSWORD")
    if not developer_email:
        return False, "Email required."
    if not sender_email or not sender_password:
        return False, "Mail credentials are not configured."

    now = time.time()
    with _lock:
        prev = DEVELOPER_OTP_STORE.get(developer_email)
        if prev and now - prev["sent_at"] < RESEND_COOLDOWN:
            return False, "Please wait before requesting another code."
        otp = f"{secrets.randbelow(900000) + 100000}"   # 100000-999999
        DEVELOPER_OTP_STORE[developer_email] = {
            "otp": otp, "expires": now + OTP_TTL_SECONDS, "attempts": 0, "sent_at": now}

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = developer_email
        msg["Subject"] = "M&K Nexus Cloud - Developer Access OTP"
        msg.attach(MIMEText(
            f"Your secure developer verification OTP is: {otp}\n"
            f"It expires in {OTP_TTL_SECONDS // 60} minutes. Do not share it.", "plain"))
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=15)
        try:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, developer_email, msg.as_string())
        finally:
            server.quit()
        return True, "OTP dispatched."
    except Exception as e:
        with _lock:
            DEVELOPER_OTP_STORE.pop(developer_email, None)   # no usable code if mail failed
        return False, str(e)


def verify_developer_otp(developer_email, entered_otp):
    developer_email = (developer_email or "").strip().lower()
    entered_otp = (entered_otp or "").strip()
    with _lock:
        rec = DEVELOPER_OTP_STORE.get(developer_email)
        if not rec:
            return False
        if time.time() > rec["expires"] or rec["attempts"] >= MAX_ATTEMPTS:
            del DEVELOPER_OTP_STORE[developer_email]
            return False
        rec["attempts"] += 1
        if hmac.compare_digest(rec["otp"], entered_otp):
            del DEVELOPER_OTP_STORE[developer_email]    # single use
            return True
        if rec["attempts"] >= MAX_ATTEMPTS:
            del DEVELOPER_OTP_STORE[developer_email]
        return False
