import os
import time
import requests

LOG_FILE = "logs/app_activity.log"
SERVER_URL = "http://127.0.0.1:5000/upload-log"

def send_logs():
    if not os.path.exists(LOG_FILE):
        os.makedirs("logs", exist_ok=True)
        with open(LOG_FILE, "w") as f:
            f.write("System started successfully.\n")

    print("Log Agent started... Monitoring logs.")

    # Usually we write a Lock Entry to Test
    with open(LOG_FILE, "a") as f:
        f.write(f"INFO: New connection test at {time.ctime()}\n")

if "__name__" == "__main__":
    send_logs()

