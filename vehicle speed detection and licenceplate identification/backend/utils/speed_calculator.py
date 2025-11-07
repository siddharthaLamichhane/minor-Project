import numpy as np
from datetime import datetime

class SpeedCalculator:
    def __init__(self, distance_meters=16.0, frame_width_pixels=400):
        self.distance_meters = distance_meters
        self.frame_width_pixels = frame_width_pixels
        self.meters_per_pixel = distance_meters / frame_width_pixels
        
    def calculate_speed(self, pixel_distance, time_seconds):
        """Calculate speed in km/h"""
        if time_seconds == 0:
            return 0
            
        meters = pixel_distance * self.meters_per_pixel
        speed_mps = meters / time_seconds
        speed_kmh = speed_mps * 3.6
        return round(speed_kmh, 2)