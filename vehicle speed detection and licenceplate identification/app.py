from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, session
from flask_login import LoginManager, login_user, login_required, logout_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from models import mongo, init_db
from models.user import User
from datetime import datetime
from flask_pymongo import PyMongo
from backend.api import api_bp
import os
import logging
from bson.objectid import ObjectId

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/monitoring'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
# Increase max content length to 500MB
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Configure logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Disable Flask's default logging
app.logger.disabled = True
log.disabled = True

# Initialize MongoDB
mongo = PyMongo(app)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'error'

# Add user loader
@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if user_data:
            return User(user_data)
    except Exception as e:
        print(f"Error loading user: {e}")
    return None

# Register API blueprint
app.register_blueprint(api_bp)

from routes import *

# After app configurations
init_db(app)

if __name__ == '__main__':
    print('\nServer is running at: http://localhost:5000')
    app.run(host='0.0.0.0', port=5000, debug=False)
    