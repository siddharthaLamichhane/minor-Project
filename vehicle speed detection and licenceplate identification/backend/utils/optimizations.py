import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor

class ImageProcessor:
    def __init__(self, max_workers=4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
    def preprocess_image(self, image):
        """Optimize image preprocessing"""
        # Resize for faster processing
        height, width = image.shape[:2]
        if width > 1000:
            scale = 1000 / width
            image = cv2.resize(image, None, fx=scale, fy=scale)
            
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        # Apply CLAHE for better contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        return gray

    async def process_batch(self, images):
        """Process multiple images in parallel"""
        futures = [
            self.executor.submit(self.preprocess_image, img)
            for img in images
        ]
        return [future.result() for future in futures]