from werkzeug.security import generate_password_hash
from pymongo import MongoClient
from datetime import datetime

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['monitoring']

# Admin credentials with a stronger password hash method
admin_user = {
    'username': 'admin',
    'email': 'admin@admin.com',
    'password': generate_password_hash('admin', method='pbkdf2:sha256'),
    'role': 'admin',
    'created': datetime.utcnow()
}

# Insert admin user if not exists
if not db.users.find_one({'email': admin_user['email']}):
    db.users.insert_one(admin_user)
    print("Admin user created successfully!")
else:
    # Update existing admin password
    db.users.update_one(
        {'email': admin_user['email']},
        {'$set': {
            'password': admin_user['password'],
            'username': admin_user['username'],
            'role': admin_user['role']
        }}
    )
    print("Admin user updated successfully!")

print("\nAdmin Login Details:")
print("Email: admin@admin.com")
print("Password: admin")