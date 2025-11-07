from flask_mail import Message, Mail
from datetime import datetime
from config.email_config import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SENDER_EMAIL

mail = Mail()

def init_mail(app):
    app.config['MAIL_SERVER'] = SMTP_SERVER
    app.config['MAIL_PORT'] = SMTP_PORT
    app.config['MAIL_USERNAME'] = SMTP_USERNAME
    app.config['MAIL_PASSWORD'] = SMTP_PASSWORD
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_DEFAULT_SENDER'] = SENDER_EMAIL
    mail.init_app(app)

class EmailSender:
    @staticmethod
    def send_violation_notification(violation_data):
        subject = f"Traffic Violation Notice - {violation_data['license_plate']}"
        body = f"""
        Dear Vehicle Owner,

        A traffic violation was recorded for your vehicle:
        
        License Plate: {violation_data['license_plate']}
        Date: {violation_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}
        Speed: {violation_data['speed']} km/h
        Speed Limit: 60 km/h
        Fine Amount: ${violation_data.get('fine_amount', 0):.2f}

        Please pay the fine within 30 days.
        
        Regards,
        Traffic Monitoring System
        """
        
        msg = Message(
            subject=subject,
            recipients=[violation_data.get('owner_email')],
            body=body
        )
        mail.send(msg)

    @staticmethod
    def send_violation_email(recipient_email, license_plate, speed, image_path):
        subject = f"Traffic Violation Notice - {license_plate}"
        body = f"""
        Dear Vehicle Owner,

        A traffic violation was recorded for your vehicle:
        
        License Plate: {license_plate}
        Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        Speed: {speed} km/h
        Speed Limit: 45 km/h

        Please pay the fine within 30 days.
        
        Regards,
        Traffic Monitoring System
        """
        
        msg = Message(
            subject=subject,
            recipients=[recipient_email],
            body=body
        )
        mail.send(msg)

def send_violation_email(recipient_email, license_plate, speed, image_path):
    EmailSender.send_violation_email(recipient_email, license_plate, speed, image_path)