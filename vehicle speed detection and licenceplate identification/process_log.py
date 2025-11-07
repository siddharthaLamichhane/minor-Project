import pandas as pd
from datetime import datetime
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from models.user_vehicle import UserVehicle
from models.violation_log import ViolationLog

def clean_plate_number(plate):
    # Remove special characters and extra spaces
    cleaned = re.sub(r'[|_~\?\{\}\[\]\(\)\\\/]', '', plate)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip('.- ')
    
    # Remove single characters at the start
    cleaned = re.sub(r'^[A-Z1-9]\s+', '', cleaned)
    
    return cleaned.strip()

def send_violation_email(user_data, speed, timestamp, image_path):
    sender_email = "your_email@gmail.com"
    sender_password = "your_app_password"
    receiver_email = user_data['email']
    
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = f"Speed Violation Alert - {user_data['license_plate']}"
    
    body = f"""
    Dear {user_data['name']},
    
    A speed violation has been detected for your vehicle:
    
    License Plate: {user_data['license_plate']}
    Speed Detected: {speed:.2f} km/h
    Speed Limit: {SPEED_LIMIT} km/h
    Time: {timestamp}
    Location: [Location Details]
    
    This is violation #{user_data['violation_count'] + 1} for your vehicle.
    
    Please maintain safe driving practices.
    
    Best regards,
    Traffic Monitoring System
    """
    
    message.attach(MIMEText(body, "plain"))
    
    if image_path and os.path.exists(image_path):
        with open(image_path, 'rb') as img_file:
            img = MIMEImage(img_file.read())
            img.add_header('Content-Disposition', 'attachment', filename=f"violation_{timestamp}.jpg")
            message.attach(img)
    
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(message)
        server.quit()
        print(f"Violation email sent to {receiver_email}")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")

def process_log():
    df = pd.read_csv('detections/log.txt', names=['timestamp', 'plate', 'speed'])
    df['plate'] = df['plate'].apply(clean_plate_number)
    
    user_db = UserVehicle()
    violation_log = ViolationLog()
    
    results = []
    unique_plates = df['plate'].unique()
    
    SPEED_LIMIT = 60
    
    for plate in unique_plates:
        if len(plate) >= 6:
            plate_data = df[df['plate'] == plate]
            user_data = user_db.get_user_by_plate(plate)
            
            if user_data:
                avg_speed = plate_data['speed'].mean()
                max_speed = plate_data['speed'].max()
                first_seen = min(plate_data['timestamp'])
                last_seen = max(plate_data['timestamp'])
                
                if max_speed > SPEED_LIMIT:
                    violation_record = plate_data[plate_data['speed'] == max_speed].iloc[0]
                    image_path = f"detections/plate_{plate}_{violation_record['timestamp']}.jpg"
                    
                    # Log violation
                    violation_log.log_violation(
                        user_data=user_data,
                        speed=max_speed,
                        timestamp=violation_record['timestamp'],
                        image_path=image_path
                    )
                    
                    # Update violation count and send email
                    user_db.update_violation_count(plate)
                    send_violation_email(
                        user_data=user_data,
                        speed=max_speed,
                        timestamp=violation_record['timestamp'],
                        image_path=image_path
                    )
                
                results.append({
                    'plate': plate,
                    'owner': user_data['name'],
                    'email': user_data['email'],
                    'avg_speed': round(avg_speed, 2),
                    'max_speed': round(max_speed, 2),
                    'first_seen': first_seen,
                    'last_seen': last_seen,
                    'violation': max_speed > SPEED_LIMIT,
                    'violation_count': user_data['violation_count']
                })
    
    # Save processed results with enhanced information
    with open('detections/processed_log.txt', 'w') as f:
        f.write("Plate,Owner,Email,Avg Speed,Max Speed,First Seen,Last Seen,Violations\n")
        for r in results:
            f.write(f"{r['plate']},{r['owner']},{r['email']},{r['avg_speed']},{r['max_speed']},"
                   f"{r['first_seen']},{r['last_seen']},{r['violation_count']}\n")