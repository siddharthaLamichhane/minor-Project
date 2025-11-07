# Speed Detection and Fine Management System

## Overview
This project is an advanced vehicle speed detection and fine management system that uses computer vision and deep learning to monitor traffic, detect speed violations, and automatically manage the fine issuance process. The system combines real-time video processing, license plate recognition, and automated notification systems to create a comprehensive traffic monitoring solution.

## Key Features
- Real-time vehicle speed detection using computer vision
- Automatic license plate recognition (ALPR)
- Speed violation detection and logging
- Automated fine calculation based on violation severity
- Email notification system for violations
- Web-based dashboard for monitoring and management
- Detailed violation reports and analytics
- User management system with role-based access
- MongoDB integration for efficient data storage

## Technical Stack
- **Backend**: Python, Flask
- **Computer Vision**: OpenCV, YOLOv8, EasyOCR
- **Database**: MongoDB
- **Frontend**: HTML, CSS, JavaScript
- **Additional Libraries**: NumPy, PyTesseract, Ultralytics

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd speed-detection-system
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Set up MongoDB:
- Install MongoDB on your system
- Start MongoDB service
- Configure connection string in config files

5. Configure email settings:
- Update email configuration in utils/email_sender.py

## Usage

1. Start the application:
```bash
python app.py
```

2. Access the web interface:
- Open a browser and navigate to `http://localhost:5000`
- Log in with admin credentials

3. Process video footage:
- Upload video files through the web interface
- Monitor real-time detection results
- View violation reports and analytics

## System Components

### 1. Video Processing Module
- Handles real-time video feed processing
- Implements vehicle detection and tracking
- Calculates vehicle speeds using pixel-to-meter conversion

### 2. License Plate Recognition
- Uses YOLOv8 for vehicle detection
- Implements EasyOCR for license plate text extraction
- Processes and validates plate numbers

### 3. Violation Management
- Automated violation detection and logging
- Fine calculation based on speed excess and repeat offenses
- Image capture and storage of violations

### 4. User Management
- Role-based access control
- Admin dashboard for system management
- User registration and authentication

### 5. Reporting System
- Generates detailed violation reports
- Provides statistical analysis and trends
- Exports data in various formats

## Configuration

Key configuration files:
- `config/config.json`: Main configuration file
- `models/yolov3.cfg`: YOLO model configuration
- `utils/email_sender.py`: Email notification settings

## Directory Structure
```
├── backend/          # Backend API and models
├── frontend/         # Web interface files
├── models/           # ML models and configurations
├── static/          # Static assets
├── templates/       # HTML templates
├── utils/           # Utility functions
└── videos/          # Video storage
```

## Contributing
Contributions are welcome! Please feel free to submit pull requests.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments
- YOLOv8 for object detection
- OpenCV community
- EasyOCR for text recognition

## Support
For support and queries, please open an issue in the repository.