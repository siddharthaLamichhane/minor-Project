# Email Configuration Settings

SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USERNAME = 'sidlamichhane99@gmail.com'  # Replace with your email
SMTP_PASSWORD = 'gnhm mdes zbhz cdrk'      # Replace with your app password
SENDER_EMAIL = 'sidlamichhane99@gmail.com'    # Replace with your email

# Email Template Settings
EMAIL_SUBJECT = 'Speed Violation Notification'
EMAIL_TEMPLATE = """
Dear {name},

This is to notify you that your vehicle with license plate {license_plate} was detected exceeding the speed limit.

Violation Details:
- Date: {date}
- Time: {time}
- Location: Speed Monitoring Zone
- Recorded Speed: {speed} km/h
- Speed Limit: {speed_limit} km/h
- Fine Amount: ${fine_amount}

Please note that you are required to pay the fine within 30 days of this notice.

Regards,
Traffic Monitoring System
"""