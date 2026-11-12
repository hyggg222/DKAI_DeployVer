# DKAI System
[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flutter](https://img.shields.io/badge/Flutter-3.0+-02569B.svg?logo=flutter)](https://flutter.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![YOLOv11](https://img.shields.io/badge/YOLO-v11-00FFFF.svg)](https://github.com/ultralytics/ultralytics)

A comprehensive AI-driven Vehicle Entry/Exit Management System with real-time license plate detection, recognition, and automated gate control.

## Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Tech Stack](#-tech-stack)
- [System Requirements](#-system-requirements)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Mobile App Setup](#-mobile-app-setup)
- [Screenshots](#-screenshots)
- [License](#-license)

## Features

- Real-time vehicle detection using YOLOv11
- License plate detection with custom fine-tuned YOLO model
- OCR and context verification with Google Gemini 2.0 Flash
- Dual camera support (entry and exit)
- Real-time WebSocket communication
- Mobile app for remote monitoring
- SQLite database with WAL mode for high concurrency
- Support for both RTSP cameras and test video files

## Quick Start

```bash
git clone https://github.com/hyggg222/DKAI_DeployVer.git
cd DKAI_DeployVer
python setup.py

# Configure .env file (Setup wizard does this, but manual option below)
# cp .env.example .env

python ai_server_test.py

# Visit http://localhost:8001
```

## Tech Stack

- **Language**: Python 3.10+
- **Backend**: FastAPI (REST API), Python-SocketIO (Real-time WebSocket)
- **AI Models**:
  - **YOLOv11** (Object Detection: Vehicles)
  - **Custom Fine-tuned YOLO** (License Plate Detection)
  - **Google Gemini 2.0 Flash Exp** (OCR & Context Verification)
- **Database**: SQLite (WAL Mode enabled for high concurrency)
- **Mobile App**: Flutter (Dart)

## Project Structure

```
DKAI_DeployVer/
├── ai_server.py              # Production server (RTSP cameras, FastAPI + Socket.IO)
├── ai_server_test.py         # Test server (video file simulation)
├── setup.py                  # Setup wizard and environment verification
├── requirements.txt          # Python dependencies
├── Dockerfile                # Container definition
├── docker-compose.yml        # Docker compose service definition
├── .env.example              # Environment configuration template
├── .gitignore               # Git ignore configuration
├── LICENSE                  # MIT License
├── README.md                # Project documentation
├── src/                     # Core AI and backend modules
│   ├── auto_trigger.py     # Vehicle tracking and line-crossing trigger logic
│   ├── camera_manager.py   # RTSP dual camera stream manager
│   ├── database.py         # SQLite logging and record management
│   ├── plate_detector.py   # License plate detector & Gemini OCR integration
│   └── vehicle_detector.py # Vehicle detection and bounding-box validation
├── weights/                 # Pre-trained weights included in repo
│   ├── license-plate-finetune-v1l.pt # License plate detection
│   ├── yolo11s.pt          # YOLOv11 vehicle detection
│   └── yolov8s.pt          # YOLOv8 vehicle detection
├── templates/              # Web interface
│   └── index.html          # Real-time monitoring dashboard
├── tests/                  # Automated test suite
│   ├── test_database.py    # Database CRUD tests
│   ├── test_server_endpoints.py # FastAPI route tests
│   ├── test_smoke.py       # Module import tests
│   └── test_vehicle_detector_logic.py # Detection algorithm tests
├── test_videos/            # Directory for user-provided test videos (.mp4)
└── mobile_flutter/         # Flutter mobile application
    ├── lib/                # Flutter/Dart source code
    ├── android/            # Android platform configuration
    ├── ios/                # iOS platform configuration
    └── pubspec.yaml        # Flutter package manifest
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/hyggg222/DKAI_DeployVer.git
cd DKAI_DeployVer
```

### 2. Set Up Python Environment

It's recommended to use a virtual environment:

```bash
python -m venv venv

# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Model Weights

Pre-trained model weights are bundled directly in the `weights/` directory:
- `weights/yolo11s.pt`: YOLOv11 small model for vehicle detection
- `weights/license-plate-finetune-v1l.pt`: Custom fine-tuned YOLO model for license plate localization
- `weights/yolov8s.pt`: Alternative YOLOv8 vehicle detection model

No additional download is required. The setup script (`python setup.py`) will automatically verify these weights.

### 5. Running with Docker (Optional)

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Configuration

### 1. Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit the `.env` file with your configuration:

```env
# Google Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# RTSP Camera URLs (for production)
RTSP_FRONT=rtsp://username:password@camera_ip:554/stream1
RTSP_BACK=rtsp://username:password@camera_ip:554/stream2

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8001

# Database Configuration
DATABASE_PATH=./vehicle_logs.db
```

### 2. Get Google Gemini API Key -> Put it in your `.env` file

### 3. RTSP Camera URLs

If you don't have RTSP cameras, you can use:
- **IP Webcam** apps (Android/iOS) to stream from your phone
- **USB cameras** with tools like `ffmpeg` to create RTSP streams
- **Test mode** with video files (see Usage section)

**RTSP URL Format Examples:**
```
rtsp://admin:password@192.168.1.100:554/stream1
rtsp://192.168.1.101:8554/cam1
rtsp://username:password@camera.example.com/live
```

## Usage

### Running the Test Server (Demo Mode)

Use this mode to verify the system without physical RTSP cameras.

To run with sample test videos, place your video files into the `test_videos/` directory:
- `test_videos/front.mp4` (Front entry camera)
- `test_videos/back.mp4` (Exit camera)

```bash
python ai_server_test.py
```

**What happens:**
- Server starts on `http://localhost:8001`
- Loops `front.mp4` and `back.mp4` from `test_videos/` (falls back to standby test frames if no videos are present)
- Simulates vehicle detection and license plate recognition
- Perfect for local testing, demos, and verification

**Access the web interface:**
- Open browser to `http://localhost:8001`
- View real-time detection status
- Monitor vehicle entry/exit logs

### Running the Production Server

Use this for real-world deployment with RTSP cameras.

```bash
python ai_server.py
```

**Configuration Options:**

**Option 1: Using .env file**
- Configure `RTSP_FRONT` and `RTSP_BACK` in `.env`
- Server automatically reads the configuration

**Option 2: Interactive Setup**
- If `.env` is not configured, the server will prompt:
  ```
  Enter RTSP URL for FRONT camera (or press Enter to use camera ID 0):
  Enter RTSP URL for BACK camera (or press Enter to use camera ID 1):
  ```
- Enter your RTSP URLs or camera IDs

**Server Access:**
- Web interface: `http://your-server-ip:8001`
- REST API: `http://your-server-ip:8001/api`
- WebSocket: `ws://your-server-ip:8001/socket.io`

### Stopping the Server

Press `Ctrl + C` in the terminal to gracefully shut down the server.

## Mobile App Setup

### Install Flutter

### Navigate to Mobile Directory

```bash
cd mobile_flutter
```

### Install Dependencies

```bash
flutter pub get
```

### Configure Server Connection

Edit `lib/config/api_config.dart` (or similar file) with your server IP:

```dart
class ApiConfig {
  // Replace with your server's IP address
  static const String baseUrl = 'http://192.168.1.100:8001';
  static const String wsUrl = 'ws://192.168.1.100:8001';
}
```

**Find your server IP:**
- **Windows**: `ipconfig` (look for IPv4 Address)
- **macOS/Linux**: `ifconfig` or `ip addr`
- The server also displays its IP on startup

### 5. Run the App

**For Android:**
```bash
flutter run
```

**For iOS:**
```bash
flutter run -d ios
```

**For a specific device:**
```bash
# List available devices
flutter devices

# Run on specific device
flutter run -d device_id
```

### 6. Build Release APK (Android)

```bash
flutter build apk --release
```

The APK will be in `build/app/outputs/flutter-apk/app-release.apk`

## Screenshots

### Web Dashboard Overview
![Web Dashboard](docs/images/dashboard.png)

### Real-Time Detection Feed
![Live Monitoring](docs/images/dashboard-live.png)

## API Documentation

### REST API Endpoints

#### Get Recent Records
```http
GET /api/history
```

**Response:**
```json
[
  {
    "id": 1,
    "timestamp": "2026-11-12 14:30:00",
    "plate": "30A12345",
    "plate_url": "/images/captures/plate_1.jpg",
    "car_url": "/images/captures/car_1.jpg",
    "status": "APPROVED",
    "note": ""
  }
]
```

### WebSocket Events

#### Connect to WebSocket
```javascript
const socket = io('http://your-server-ip:8001');
```

#### Listen for Vehicle Detection
```javascript
socket.on('vehicle_detected', (data) => {
  console.log(data);
  // {
  //   plate_number: "ABC1234",
  //   camera: "front",
  //   timestamp: "2025-01-10 14:30:00",
  //   confidence: 0.95
  // }
});
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Contact

For questions or support, please open an issue on GitHub.
