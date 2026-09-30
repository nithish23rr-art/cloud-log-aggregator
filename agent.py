import requests
import time
import random

# சென்ட்ரல் பிளாஸ்க் சர்வர் முகவரி
SERVER_URL = "http://127.0.0.1:5000/add_log"

LOG_LEVELS = ["INFO", "WARNING", "ERROR"]
SAMPLE_MESSAGES = {
    "INFO": [
        "System health check passed successfully.",
        "User session authenticated via OAuth2.",
        "Database connection pool initialized.",
        "Cache cleared and reloaded."
    ],
    "WARNING": [
        "High memory utilization detected (>85%).",
        "API response latency is higher than expected.",
        "Disk space running low on volume /dev/sda1."
    ],
    "ERROR": [
        "Database connection timeout encountered!",
        "Failed to process incoming payment transaction.",
        "Critical server exception in auth module!"
    ]
}

# பல வெவ்வேறு கிளவுட் சர்வர்களின் ஐபி முகவரிகளைப் போல சிமுலேஷன் செய்தல்
SERVER_IPS = [
    "192.168.1.10", 
    "10.0.0.25", 
    "172.16.0.5", 
    "192.168.1.50"
]

def send_log_to_server():
    level = random.choice(LOG_LEVELS)
    message = random.choice(SAMPLE_MESSAGES[level])
    fake_ip = random.choice(SERVER_IPS)
    
    try:
        data = {
            'message': message,
            'level': level
        }
        # போலி ஐபி முகவரியை ஹெடரில் இணைத்து அனுப்புதல் (Custom Header for Simulation)
        headers = {
            'X-Forwarded-For': fake_ip
        }
        
        response = requests.post(SERVER_URL, data=data, headers=headers)
        if response.status_code == 200:
            print(f"Log sent from IP [{fake_ip}] : [{level}] {message}")
        else:
            print("Failed to send log, Status code:", response.status_code)
    except Exception as e:
        print("Error connecting to server:", e)

if _name_ == "_main_":
    print("Enterprise Log Agent is running and sending simulated multi-server logs...")
    while True:
        send_log_to_server()
        # ஒவ்வொரு 6 விநாடிகளுக்கு ஒருமுறை லாக் அனுப்பப்படும்
        time.sleep(6)