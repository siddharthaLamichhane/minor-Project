import cv2
import numpy as np
import os

class VehicleSpeedDetector:
    def __init__(self):
        self.net = None
        self.output_layers = None
        self.classes = None
        self.initialize_model()
    
    def initialize_model(self):
        # Use absolute paths
        base_dir = r"c:\Users\DELL\Desktop\number plate"
        model_dir = os.path.join(base_dir, 'models')
        weights_path = os.path.join(model_dir, "yolov3.weights")
        config_path = os.path.join(model_dir, "yolov3.cfg")
        names_path = os.path.join(model_dir, "coco.names")
        
        # Verify files exist
        if not os.path.exists(weights_path):
            raise FileNotFoundError(f"YOLO weights file not found at: {weights_path}")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"YOLO config file not found at: {config_path}")
        if not os.path.exists(names_path):
            raise FileNotFoundError(f"COCO names file not found at: {names_path}")
        
        # Load the network
        print(f"Loading YOLO model from: {config_path} and {weights_path}")
        self.net = cv2.dnn.readNet(weights_path, config_path)
        
        # Load classes
        with open(names_path, "r") as f:
            self.classes = [line.strip() for line in f.readlines()]
        
        layer_names = self.net.getLayerNames()
        self.output_layers = [layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
    
    def detect_vehicles(self, frame):
        height, width, _ = frame.shape
        blob = cv2.dnn.blobFromImage(frame, 0.00392, (416, 416), (0, 0, 0), True, crop=False)
        
        self.net.setInput(blob)
        outs = self.net.forward(self.output_layers)
        
        # Process detections
        class_ids = []
        confidences = []
        boxes = []
        
        for out in outs:
            for detection in out:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                if confidence > 0.5 and class_id in [2, 3, 5, 7]:  # car, motorbike, bus, truck
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
        
        return boxes, confidences, class_ids