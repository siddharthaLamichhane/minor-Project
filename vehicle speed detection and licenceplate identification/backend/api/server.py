from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime
import uvicorn
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.models.user import User
from backend.models.vehicle_detection import VehicleDetection

app = FastAPI(
    title="Vehicle Detection API",
    description="API for vehicle license plate detection and monitoring",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic health check endpoint
@app.get("/")
async def root():
    return {"message": "Vehicle Detection API is running"}

@app.get("/health")
async def health_check():
    try:
        # Check MongoDB connection
        vehicle_db.client.server_info()
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unavailable")

@app.post("/api/detection")
async def record_detection(plate_number: str, speed: float, image: UploadFile = File(...)):
    try:
        # Save image
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_path = f"detections/{timestamp}_{plate_number}.jpg"
        with open(image_path, "wb") as buffer:
            buffer.write(await image.read())
        
        # Record in database
        vehicle_detection = VehicleDetection()
        detection_id = vehicle_detection.insert_detection(
            plate_number=plate_number,
            speed=speed,
            image_path=image_path
        )
        
        # Check for violation
        if speed > 70:  # Speed limit
            violation_data = {
                'plate_number': plate_number,
                'speed': speed,
                'timestamp': datetime.utcnow(),
                'image_path': image_path,
                'status': 'pending'
            }
            vehicle_detection.collection.insert_one(violation_data)
        
        return {"status": "success", "detection_id": str(detection_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/violations")
async def get_violations(start_date: str = None, end_date: str = None):
    try:
        vehicle_detection = VehicleDetection()
        violations = vehicle_detection.get_violations(
            start_date=datetime.fromisoformat(start_date) if start_date else None,
            end_date=datetime.fromisoformat(end_date) if end_date else None
        )
        
        formatted_violations = [{
            'plate_number': v['plate_number'],
            'speed': v['speed'],
            'timestamp': v['timestamp'].isoformat(),
            'image_path': v['image_path'],
            'status': v.get('status', 'pending')
        } for v in violations]
        
        return {"violations": formatted_violations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Start server if running directly
if __name__ == "__main__":
    os.makedirs("detections", exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")