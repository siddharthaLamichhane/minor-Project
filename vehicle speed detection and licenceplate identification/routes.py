from app import app
from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import mongo
from models.user import User
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import os
from video_processor import VideoProcessor
from vehicle_speed_detector import VehicleSpeedDetector  # Add this import
from clear_violations import clear_violations

# Global variable to track video processing status
video_processing = False

from flask_login import current_user
import threading

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Stop redirect loop by checking authentication
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not email or not password:
            flash('Please provide both email and password', 'error')
            return render_template('login.html')
        
        user = User.get_by_email(email)
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        
        flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/check_processing_status')
@login_required
def check_processing_status():
    global video_processing
    return jsonify({'is_processing': video_processing})

@app.route('/clear_violations', methods=['POST'])
@login_required
def clear_all_violations():
    try:
        if clear_violations():
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Failed to delete violations'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/dashboard')
@login_required
def dashboard():
    # Remove the authentication check since @login_required handles it
    try:
        total_violations = mongo.db.violations.count_documents({})
        total_users = mongo.db.users.count_documents({})
        return render_template('dashboard.html',
                             total_violations=total_violations,
                             total_users=total_users)
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/users')
@login_required
def users():
    try:
        # Get only active users from the database
        users_list = list(mongo.db.users.find({'is_active': {'$ne': False}}))
        formatted_users = [{
            'id': str(user['_id']),
            'username': user.get('username'),
            'email': user.get('email'),
            'role': user.get('role', 'user'),
            'license_plate': user.get('license_plate')
        } for user in users_list]
        return render_template('users.html', users=formatted_users)
    except Exception as e:
        flash(f'Error loading users: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        license_plate = request.form.get('license_plate')
        phone = request.form.get('phone')

        # Check if email or license plate exists
        if mongo.db.users.find_one({'email': email}):
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        if mongo.db.users.find_one({'license_plate': license_plate}):
            flash('License plate already registered', 'error')
            return redirect(url_for('register'))

        # Register vehicle user
        user_data = {
            'username': username,
            'email': email,
            'license_plate': license_plate,
            'phone': phone,
            'role': 'user',
            'created': datetime.utcnow()
        }
        
        try:
            mongo.db.users.insert_one(user_data)
            flash('Registration successful! You can now login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error during registration: {str(e)}', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if request.method == 'GET':
        return render_template('register.html')
    try:
        data = request.get_json()
        
        # Check if email exists
        if mongo.db.users.find_one({'email': data['email']}):
            return jsonify({'error': 'Email already exists'})
        
        user_data = {
            'username': data['username'],
            'email': data['email'],
            'password': generate_password_hash(data['password']),
            'role': data['role'],
            'created': datetime.utcnow()
        }
        
        result = mongo.db.users.insert_one(user_data)
        return jsonify({'success': True, 'id': str(result.inserted_id)})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/update_user', methods=['POST'])
@login_required
def update_user():
    try:
        data = request.get_json()
        update_data = {
            'username': data['username'],
            'email': data['email'],
            'role': data['role']
        }
        
        if data['password']:
            update_data['password'] = generate_password_hash(data['password'])
        
        result = mongo.db.users.update_one(
            {'_id': ObjectId(data['id'])},
            {'$set': update_data}
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'User not found'})
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/delete_user', methods=['POST'])
@login_required
def delete_user():
    try:
        data = request.get_json()
        result = mongo.db.users.delete_one({'_id': ObjectId(data['id'])})
        
        if result.deleted_count == 0:
            return jsonify({'error': 'User not found'})
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/violations')
@login_required
def violations():
    try:
        # Get all violations from the database without any limit
        violations_list = list(mongo.db.violations.find().sort('timestamp', -1))
        formatted_violations = []
        
        for violation in violations_list:
            # Only process violations that have all required fields
            if all(key in violation for key in ['_id', 'timestamp', 'license_plate', 'speed', 'image_path']):
                # Ensure image path is properly formatted for static file serving
                image_path = violation['image_path']
                if image_path and not image_path.startswith('static/'):
                    image_path = f"static/violations/{os.path.basename(image_path)}"
                
                # Verify image file exists
                full_image_path = os.path.join(app.static_folder, 'violations', os.path.basename(image_path))
                if not os.path.exists(full_image_path):
                    continue
                
                formatted_violations.append({
                    '_id': str(violation['_id']),
                    'date': violation['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                    'license_plate': violation['license_plate'],
                    'speed': violation['speed'],
                    'image_path': image_path,
                    'status': 'Violation' if violation['speed'] > 45 else 'Normal'  # Speed limit set to 45 km/h
                })
            
        return render_template('violations.html', violations=formatted_violations)
    except Exception as e:
        flash(f'Error loading violations: {str(e)}', 'error')
        return redirect(url_for('dashboard'))






@app.route('/processing_status')
@login_required
def processing_status():
    try:
        # Get latest video status
        latest_video = mongo.db.videos.find_one(
            {'uploaded_by': str(current_user.id)},
            sort=[('uploaded_at', -1)]
        )
        
        if not latest_video:
            return jsonify({'status': 'no_video'})
            
        return jsonify({
            'status': latest_video.get('status', 'unknown'),
            'progress': latest_video.get('progress', 0),
            'error': latest_video.get('error_message'),
            'detections': latest_video.get('detections', [])
        })
        
    except Exception as e:
        print(f"Status check error: {str(e)}")
        return jsonify({'error': str(e)})

@app.route('/get_latest_violations')
@login_required
def get_latest_violations():
    try:
        # Get the latest violations from the database
        violations_list = list(mongo.db.violations.find().sort('timestamp', -1).limit(50))
        formatted_violations = []
        
        for violation in violations_list:
            # Ensure image path is properly formatted for static file serving
            image_path = violation.get('image_path', '')
            if image_path and not image_path.startswith('static/'):
                image_path = f"static/violations/{os.path.basename(image_path)}"
            
            formatted_violations.append({
                '_id': str(violation['_id']),
                'date': violation.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M:%S'),
                'license_plate': violation.get('license_plate', 'Unknown'),
                'speed': violation.get('speed', 0),
                'image_path': image_path,
                'status': 'Violation' if violation.get('speed', 0) > 45 else 'Normal'  # Speed limit set to 45 km/h
            })
        
        return jsonify({'success': True, 'violations': formatted_violations})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/upload_video', methods=['POST'])
@login_required
def upload_video():
    try:
        global video_processing
        
        if 'video' not in request.files:
            return jsonify({'error': 'No video file uploaded'}), 400
            
        video_file = request.files['video']
        if video_file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        # Ensure the upload directory exists
        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'videos')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Save the uploaded file
        filename = secure_filename(video_file.filename)
        filepath = os.path.join(upload_dir, filename)
        video_file.save(filepath)
        
        # Create a video document in MongoDB
        video_data = {
            'filename': filename,
            'filepath': filepath,
            'uploaded_by': str(current_user.id),
            'uploaded_at': datetime.utcnow(),
            'status': 'pending',
            'progress': 0
        }
        mongo.db.videos.insert_one(video_data)
        
        # Initialize video processor and start processing
        processor = VideoProcessor()
        status_dict = {'progress': 0, 'status': 'processing'}
        
        # Start video processing in a separate thread
        def process_video_async():
            try:
                global video_processing
                video_processing = True
                processor.process_video(filepath, status_dict)
                mongo.db.videos.update_one(
                    {'filepath': filepath},
                    {'$set': {'status': 'completed'}}
                )
            except Exception as e:
                mongo.db.videos.update_one(
                    {'filepath': filepath},
                    {'$set': {
                        'status': 'error',
                        'error_message': str(e)
                    }}
                )
            finally:
                video_processing = False
        
        thread = threading.Thread(target=process_video_async)
        thread.start()
        
        return jsonify({'success': True, 'message': 'Video upload successful, processing started'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/email_notifications')
@login_required
def email_notifications():
    try:
        notifications = list(mongo.db.email_notifications.find().sort('sent_date', -1))
        formatted_notifications = [{
            'id': str(notification['_id']),
            'violation_id': str(notification['violation_id']),
            'email': notification['email'],
            'status': notification['status'],
            'sent_date': notification['sent_date'].strftime('%Y-%m-%d %H:%M:%S')
        } for notification in notifications]
        
        return render_template('email_notifications.html', notifications=formatted_notifications)
    except Exception as e:
        flash(f'Error loading email notifications: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/resend_notification', methods=['POST'])
@login_required
def resend_notification():
    try:
        data = request.get_json()
        violation_id = ObjectId(data['violation_id'])
        
        violation = mongo.db.violations.find_one({'_id': violation_id})
        if not violation:
            return jsonify({'success': False, 'error': 'Violation not found'})
        
        if 'owner_email' not in violation:
            return jsonify({'success': False, 'error': 'No email address associated with this violation'})
        
        send_violation_email(
            violation['owner_email'],
            violation['license_plate'],
            violation['speed'],
            violation['image_path']
        )
        
        notification_data = {
            'violation_id': violation_id,
            'email': violation['owner_email'],
            'status': 'sent',
            'sent_date': datetime.utcnow()
        }
        mongo.db.email_notifications.insert_one(notification_data)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/reports')
@login_required
def reports():
    try:
        # Get statistics for the reports page
        total_violations = mongo.db.violations.count_documents({})
        recent_violations = list(mongo.db.violations.find().sort('timestamp', -1).limit(5))
        
        # Calculate daily statistics
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        daily_violations = mongo.db.violations.count_documents({'timestamp': {'$gte': today}})
        
        # Calculate weekly statistics
        week_ago = today - timedelta(days=7)
        weekly_violations = mongo.db.violations.count_documents({'timestamp': {'$gte': week_ago}})
        
        return render_template('reports.html',
                             total_violations=total_violations,
                             daily_violations=daily_violations,
                             weekly_violations=weekly_violations,
                             recent_violations=recent_violations)
    except Exception as e:
        flash(f'Error loading reports: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

@app.route('/delete_violation', methods=['POST'])
@login_required
def delete_violation():
    try:
        data = request.get_json()
        violation_id = data.get('id')
        
        if not violation_id:
            return jsonify({'success': False, 'error': 'No violation ID provided'})
            
        result = mongo.db.violations.delete_one({'_id': ObjectId(violation_id)})
        
        if result.deleted_count == 0:
            return jsonify({'success': False, 'error': 'Violation not found'})
            
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})