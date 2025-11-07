from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User:
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['monitoring']
        self.collection = self.db['users']

    def create_user(self, username, password, email=None):
        if self.collection.find_one({'username': username}):
            return None
        
        user = {
            'username': username,
            'password': generate_password_hash(password),
            'email': email,
            'created_at': datetime.utcnow(),
            'is_active': True
        }
        return self.collection.insert_one(user).inserted_id

    def verify_user(self, username, password):
        user = self.collection.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            return user
        return None