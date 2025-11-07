from ultralytics import YOLO
import cv2
import easyocr
import numpy as np
from datetime import datetime
import os
import threading
from models.database import Database
from utils.email_sender import EmailSender
from sort import Sort
import pymongo
from backend.models.vehicle_detection import VehicleDetection
from models.violation_log import ViolationLog

class VideoProcessor:
    def __init__(self, detector=None):
        self.frame_rate = 30
        self.pixels_per_meter = 100
        self.previous_positions = {}
        self.speed_limit = 45
        self.min_speed = 5  # Minimum detectable speed in km/h
        self.confidence_threshold = 0.9  # 85% confidence threshold
        self.vehicle_tracking = {}
        self.previous_positions = {}
        self.detection_db = VehicleDetection()
        self.violation_log = ViolationLog()
        
        # Load YOLOv8 models
        self.vehicle_model = YOLO('yolov8n.pt')
        self.plate_model = YOLO('yolov8.pt')
        print("YOLOv8 models loaded successfully")

    def process_video(self, filepath, status_dict, min_confidence=0.3):
        try:
            cap = cv2.VideoCapture(filepath)
            if not cap.isOpened():
                raise Exception("Error opening video file")

            self.frame_rate = self.get_frame_rate(cap)
            frame_count = 0
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            db = Database()
            
            print("\n=== Starting Video Processing ===")
            print(f"Frame Size: {int(cap.get(3))}x{int(cap.get(4))}")
            print(f"Total Frames: {total_frames}")
            print(f"Frame Rate: {self.frame_rate} fps")
            print("\nProcessing frames for vehicle detection and speed calculation...\n")

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_count += 1
                if frame_count % 5 != 0:  # Process every 5th frame
                    continue

                # Calculate and display progress
                remaining_frames = total_frames - frame_count
                progress_percent = (frame_count / total_frames) * 100
                print(f"\rProcessing: {frame_count}/{total_frames} frames ({progress_percent:.1f}%) | Remaining: {remaining_frames} frames", end="")

                processed_frame, detections = self.detect_license_plate(frame, frame_count)
                
                # Clear previous line and print frame processing status
                print('\033[K', end='\r')  # Clear line
                print(f"\r[Frame {frame_count}/{total_frames}] Processing... ", end="")
                
                if detections:
                    for detection in detections:
                        license_plate = detection.get('license_plate')
                        speed = detection.get('speed', 0)
                        confidence = detection.get('confidence', 0)
                        bbox = detection.get('bbox', [])
                        
                        if confidence >= self.confidence_threshold and speed >= self.min_speed:
                            # Use colors for better visibility
                            is_violation = speed > self.speed_limit
                            color = '\033[91m' if is_violation else '\033[92m'  # Red for violation, Green for normal
                            reset = '\033[0m'
                            
                            print(f"\n\n{color}🚗 Vehicle Detection [Frame {frame_count}]{reset}")
                            print(f"{color}├── Coordinates: (x={bbox[0]:.1f}, y={bbox[1]:.1f}){reset}")
                            print(f"{color}├── Dimensions: (w={bbox[2]:.1f}, h={bbox[3]:.1f}){reset}")
                            print(f"{color}├── License Plate: {license_plate} (Confidence: {confidence:.2%}){reset}")
                            print(f"{color}└── Speed: {speed:.1f} km/h{reset}")
                            
                            if is_violation:
                                print(f"\n{color}⚠️  SPEED VIOLATION DETECTED!{reset}")
                                print(f"{color}    Speed: {speed:.1f} km/h (Limit: {self.speed_limit} km/h){reset}")
                                
                                # Save violation image
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                image_path = f"static/violations/{timestamp}.jpg"
                                cv2.imwrite(image_path, processed_frame)
                                print(f"    📸 Violation image saved: {image_path}")
                                
                                # Log violation in database
                                violation_data = {
                                    'license_plate': license_plate,
                                    'speed': speed,
                                    'confidence': confidence,
                                    'timestamp': datetime.now(),
                                    'image_path': image_path,
                                    'status': 'Violation',
                                    'coordinates': {
                                        'x': bbox[0],
                                        'y': bbox[1],
                                        'width': bbox[2],
                                        'height': bbox[3]
                                    }
                                }
                                violation_id = db.save_violation(license_plate, speed, image_path)
                                
                                # Update MongoDB directly to ensure real-time updates
                                mongo_client = pymongo.MongoClient('mongodb://localhost:27017/')
                                db_traffic = mongo_client['traffic_monitoring']
                                db_traffic.violations.insert_one(violation_data)
                                mongo_client.close()
                                
                                print(f"    💾 Violation logged with ID: {violation_id}")
                                print("    ----------------------------------------")
                                
                                if 'violations' not in status_dict:
                                    status_dict['violations'] = []
                                status_dict['violations'].append(violation_data)
                                
                                # Get vehicle owner and send email notification
                                owner = db.get_vehicle_owner(license_plate)
                                if owner and 'email' in owner:
                                    try:
                                        violation_data = {
                                            'license_plate': license_plate,
                                            'speed': speed,
                                            'timestamp': datetime.now(),
                                            'owner_email': owner['email'],
                                            'fine_amount': violation_data.get('fine_amount', 0)
                                        }
                                        EmailSender.send_violation_notification(violation_data)
                                        print(f"📧 Violation notification sent to: {owner['email']}")
                                        db.save_email_notification(violation_id, owner['email'], 'sent')
                                    except Exception as e:
                                        print(f"Error sending email notification: {str(e)}")
                                        db.save_email_notification(violation_id, owner['email'], 'failed')
                    
                    status_dict['detections'] = detections
                    print("\n🚗 Vehicle Detection:")
                    print(f"• License Plate: {detection['license_plate']}")
                    print(f"• Speed: {detection['speed']:.1f} km/h")
                    if detection['speed'] > self.speed_limit:
                        print(f"⚠️ SPEED VIOLATION! Limit: {self.speed_limit} km/h")
                        self.save_violation(detection['license_plate'], detection['speed'], frame)

                # Try to display frame, but don't crash if display is not available
                try:
                    cv2.imshow('Speed Detection', processed_frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                except Exception as e:
                    # Silently continue if display fails
                    pass

                processed_frames = frame_count
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                status_dict.update({
                    'progress': int((processed_frames / total_frames) * 100),
                    'frames_processed': processed_frames
                })

            cap.release()
            cv2.destroyAllWindows()
            print("\n=== Video Processing Complete ===\n")
            
            # Display summary of all detections
            print("\n📊 Detection Summary")
            print("====================")
            
            unique_detections = {}
            if 'detections' in status_dict:
                for detection in status_dict['detections']:
                    plate = detection.get('license_plate')
                    speed = detection.get('speed', 0)
                    confidence = detection.get('confidence', 0)
                    
                    if plate and plate not in unique_detections:
                        unique_detections[plate] = {
                            'speed': speed,
                            'confidence': confidence
                        }
            
            if unique_detections:
                for plate, data in unique_detections.items():
                    speed = data['speed']
                    confidence = data['confidence']
                    is_violation = speed > self.speed_limit
                    
                    # Color coding: Red for violations, Green for normal
                    color = '\033[91m' if is_violation else '\033[92m'
                    reset = '\033[0m'
                    
                    print(f"{color}License Plate: {plate}{reset}")
                    print(f"├── Speed: {speed:.1f} km/h")
                    print(f"└── Confidence: {confidence:.1%}\n")
            else:
                print("No vehicles detected in this video.\n")
            
            print("=== End of Processing ===\n")
            return True

        except Exception as e:
            print(f"Error in process_video: {str(e)}")
            return False

    def detect_and_process_frame(self, frame):
        # Detect vehicles using YOLOv8
        vehicle_results = self.vehicle_model(frame)
        
        plate_img = None
        plate_text = None
        speed = 0
        
        # Process each detected vehicle
        for vehicle_box in vehicle_results[0].boxes.xyxy:
            x1, y1, x2, y2 = map(int, vehicle_box[:4].tolist())
            vehicle_img = frame[y1:y2, x1:x2]
            
            # Draw vehicle bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Detect license plate in vehicle region
            plate_results = self.plate_model(vehicle_img)
            
            if len(plate_results[0].boxes) > 0:
                # Get the first detected license plate
                plate_box = plate_results[0].boxes.xyxy[0]
                px1, py1, px2, py2 = map(int, plate_box[:4].tolist())
                
                # Extract license plate image
                plate_img = vehicle_img[py1:py2, px1:px2]
                
                # Process plate image for OCR
                plate_gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
                _, plate_thresh = cv2.threshold(plate_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                try:
                    # Use EasyOCR for better accuracy
                    reader = easyocr.Reader(['en'])
                    plate_text = reader.readtext(plate_thresh, detail=0)
                    plate_text = ''.join(plate_text).replace(' ', '').upper()
                    
                    if len(plate_text) >= 6 and '-' in plate_text:
                        plate_text = plate_text.replace('|', '').replace('_', '').strip()
                        centroid = (x1 + (x2-x1)//2, y1 + (y2-y1)//2)
                        
                        # Calculate speed
                        if plate_text in self.previous_positions:
                            prev_pos = self.previous_positions[plate_text]
                            pixel_distance = np.sqrt((centroid[0] - prev_pos[0])**2 + (centroid[1] - prev_pos[1])**2)
                            time_diff = 5 / self.frame_rate  # 5 frames between detections
                            speed = (pixel_distance * 3.6) / (time_diff * self.pixels_per_meter)
                            
                            # Draw speed and plate info
                            is_violation = speed > self.speed_limit
                            color = (0, 0, 255) if is_violation else (0, 255, 0)  # Red for violation, Green for normal
                            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
                            
                            # Add text background for better visibility
                            text = f"{plate_text} {speed:.1f}km/h"
                            (text_width, text_height), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.75, 2)
                            cv2.rectangle(frame, (x1, y1 - text_height - 10), (x1 + text_width + 10, y1), color, -1)
                            cv2.putText(frame, text, (x1 + 5, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
                            
                            if is_violation:
                                warning_text = "SPEED VIOLATION!"
                                cv2.putText(frame, warning_text, (x1, y1 - text_height - 15), 
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 255), 2)
                        
                        self.previous_positions[plate_text] = centroid
                        return plate_img, plate_text, speed
                except Exception as e:
                    print(f"OCR Error: {str(e)}")
                    continue
        
        return None, None, 0

    def get_frame_rate(self, cap):
        """Get the frame rate of the video capture."""
        fps = cap.get(cv2.CAP_PROP_FPS)
        return fps if fps > 0 else 30.0  # Default to 30 fps if unable to determine

    def detect_license_plate(self, frame, frame_count):
        # Process frame using detect_and_process_frame
        plate_img, plate_text, speed = self.detect_and_process_frame(frame)
        
        detections = []
        if plate_text and speed > 0:
            # Create detection object with confidence threshold
            detection = {
                'license_plate': plate_text,
                'speed': speed,
                'confidence': 0.9,  # High confidence for successful detections
                'bbox': [0, 0, frame.shape[1], frame.shape[0]]  # Full frame as bbox
            }
            detections.append(detection)
        
        return frame, detections

    def save_violation(self, license_plate, speed, frame):
        """Save violation details and image."""
        try:
            # Create violations directory if it doesn't exist
            os.makedirs('static/violations', exist_ok=True)
            
            # Generate timestamp and save violation image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = f"static/violations/{timestamp}.jpg"
            cv2.imwrite(image_path, frame)
            
            # Log violation in database
            violation_data = {
                'license_plate': license_plate,
                'speed': speed,
                'timestamp': datetime.now(),
                'image_path': image_path
            }
            self.violation_log.add_violation(violation_data)
            
            return True
        except Exception as e:
            print(f"Error saving violation: {str(e)}")
            return False