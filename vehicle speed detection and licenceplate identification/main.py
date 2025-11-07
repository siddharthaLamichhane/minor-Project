import cv2
import numpy as np
import pytesseract
import os
from datetime import datetime
import math

class VehicleSpeedDetector:
    def __init__(self):
        self.pytesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pytesseract.pytesseract.tesseract_cmd = self.pytesseract_path
        
        # Parameters for speed calculation
        self.frame_count = 0
        self.previous_centroid = None
        self.previous_plate = None
        self.real_world_width = 2.5  # meters (average car width)
        self.fps = None
        
    def detect_plate(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 13, 15, 15)
        edged = cv2.Canny(gray, 30, 200)
        
        contours = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = contours[0] if len(contours) == 2 else contours[1]
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
        
        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.018 * peri, True)
            
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                # Add size constraints for plate detection
                if w/h > 1.5 and w/h < 4:  # typical license plate aspect ratio
                    plate_img = frame[y:y+h, x:x+w]
                    
                    # Preprocess for OCR
                    plate_gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
                    _, plate_thresh = cv2.threshold(plate_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    
                    # OCR with custom configuration
                    try:
                        plate_text = pytesseract.image_to_string(
                            plate_thresh,
                            config='--psm 7 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'
                        ).strip()
                        
                        # Basic validation of plate format
                        if len(plate_text) >= 6 and '-' in plate_text:
                            plate_text = plate_text.replace('|', '').replace('_', '').strip()
                            centroid = (x + w//2, y + h//2)
                            return plate_img, plate_text, centroid
                    except:
                        continue
        
        return None, None, None

    def calculate_speed(self, current_centroid, frame_difference):
        if self.previous_centroid is None:
            self.previous_centroid = current_centroid
            return 0
        
        pixel_distance = math.sqrt(
            (current_centroid[0] - self.previous_centroid[0])**2 +
            (current_centroid[1] - self.previous_centroid[1])**2
        )
        
        # Adjusted scale factor for more realistic speeds
        meters = pixel_distance * self.real_world_width / 200  # Reduced scale factor
        
        time_diff = frame_difference / self.fps
        speed = (meters / time_diff) * 3.6
        
        # Add speed constraints
        speed = min(max(speed, 0), 120)  # Limit speed between 0 and 120 km/h
        
        self.previous_centroid = current_centroid
        return speed

    def process_video(self, video_path, status_dict=None):
        cap = cv2.VideoCapture(video_path)
        self.fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Create output directories
        os.makedirs("static/uploads/detections", exist_ok=True)
        output_path = os.path.join("static/uploads/detections", f"processed_{os.path.basename(video_path)}")
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(
            output_path,
            fourcc,
            self.fps,
            (int(cap.get(3)), int(cap.get(4)))
        )
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            self.frame_count += 1
            
            # Update processing status
            if status_dict is not None:
                progress = int((self.frame_count / total_frames) * 100)
                status_dict['progress'] = progress
            
            # Process every 5th frame for performance
            if self.frame_count % 5 != 0:
                continue
                
            # Detect license plate
            plate_img, plate_text, centroid = self.detect_plate(frame)
            
            if plate_text and centroid:
                speed = self.calculate_speed(centroid, 5)
                
                # Draw results on frame
                cv2.putText(frame, f"Plate: {plate_text}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, f"Speed: {speed:.2f} km/h", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # Save detection if it's a new plate
                if plate_text != self.previous_plate:
                    detection_info = self.save_detection(plate_img, plate_text, speed)
                    if status_dict is not None:
                        status_dict['detections'].append(detection_info)
                    self.previous_plate = plate_text
            
            out.write(frame)
        
        cap.release()
        out.release()
        
        if status_dict is not None:
            status_dict['status'] = 'completed'
            status_dict['progress'] = 100
        
        return output_path

    def save_detection(self, plate_img, plate_text, speed):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        detection_dir = os.path.join("static", "uploads", "detections")
        os.makedirs(detection_dir, exist_ok=True)
        
        filename = f"plate_{plate_text}_{timestamp}.jpg"
        filepath = os.path.join(detection_dir, filename)
        cv2.imwrite(filepath, plate_img)
        
        detection_info = {
            'timestamp': timestamp,
            'plate': plate_text,
            'speed': speed,
            'image_path': os.path.join("detections", filename)
        }
        
        return detection_info

def main():
    # Create detections directory if it doesn't exist
    os.makedirs("detections", exist_ok=True)
    
    detector = VehicleSpeedDetector()
    
    # Process video
    video_path = "videos/traffic.mp4"  # Add your video file
    if os.path.exists(video_path):
        detector.process_video(video_path)
    else:
        print(f"Error: Video file not found at {video_path}")

if __name__ == "__main__":
    main()