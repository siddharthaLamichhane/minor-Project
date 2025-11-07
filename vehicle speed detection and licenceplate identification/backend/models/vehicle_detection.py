from datetime import datetime
from pymongo import MongoClient
from bson import ObjectId

class VehicleDetection:
    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['monitoring']
        self.collection = self.db['detections']

    def insert_detection(self, plate_number, speed, image_path, location=None):
        detection = {
            'plate_number': plate_number,
            'speed': speed,
            'timestamp': datetime.utcnow(),
            'image_path': image_path,
            'location': location,
            'violation': speed > 70  # Configure speed limit
        }
        return self.collection.insert_one(detection).inserted_id

    def get_violations(self, start_date=None, end_date=None):
        query = {'violation': True}
        if start_date and end_date:
            query['timestamp'] = {
                '$gte': start_date,
                '$lte': end_date
            }
        return list(self.collection.find(query))

    def get_detection_by_plate(self, plate_number):
        return list(self.collection.find({'plate_number': plate_number}))