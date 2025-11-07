from celery import Celery
from models import mongo
import cv2
import numpy as np
from datetime import datetime

celery = Celery('tasks', broker='redis://localhost:6379/0')

@celery.task
def process_video(video_path):
    try:
        # Update status
        mongo.db.videos.update_one(
            {'filepath': video_path},
            {'$set': {'status': 'processing'}}
        )
        
        # Process video frames
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        processed_frames = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Your video processing logic here
            # Example:
            # - Detect license plate
            # - Calculate speed
            # - Check for violations
            
            processed_frames += 1
            progress = (processed_frames / total_frames) * 100
            
            # Update progress in database
            mongo.db.videos.update_one(
                {'filepath': video_path},
                {'$set': {'progress': progress}}
            )
        
        cap.release()
        
        # Mark as completed
        mongo.db.videos.update_one(
            {'filepath': video_path},
            {'$set': {
                'status': 'completed',
                'processed': True,
                'completion_time': datetime.utcnow()
            }}
        )
        
    except Exception as e:
        mongo.db.videos.update_one(
            {'filepath': video_path},
            {'$set': {
                'status': 'error',
                'error_message': str(e)
            }}
        )