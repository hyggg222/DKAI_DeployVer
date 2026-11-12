# DKAI System
[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flutter](https://img.shields.io/badge/Flutter-3.0+-02569B.svg?logo=flutter)](https://flutter.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![YOLOv11](https://img.shields.io/badge/YOLO-v11-00FFFF.svg)](https://github.com/ultralytics/ultralytics)

An AI-powered Vehicle Entry/Exit Monitoring & Logging System featuring real-time vehicle detection, custom license plate localization, multimodal OCR verification, and manual staff approval workflows.

## Demo

### Web Dashboard Interface
<video src="docs/videos/dashboard_demo.mp4" controls="controls" width="100%"></video>

> **Direct Video Link**: [docs/videos/dashboard_demo.mp4](docs/videos/dashboard_demo.mp4) (H.264/AAC for cross-browser playback)

![Web Dashboard](docs/images/dashboard.png)
![Live Monitoring](docs/images/dashboard-live.png)

### Mobile App
<video src="docs/videos/mobile_demo.mp4" controls="controls" width="50%"></video>

> **Direct Video Link**: [docs/videos/mobile_demo.mp4](docs/videos/mobile_demo.mp4) (Cropped mobile interface demo)

## Table of Contents

- [Demo](#demo)
- [Results & Evaluation](#results--evaluation)
- [Features](#features)
- [Quick Start](#quick-start)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Mobile App Setup](#mobile-app-setup)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [License](#license)

## Results & Evaluation

The system was evaluated using test recordings and live capture sessions at an active vehicle gate over a 2-week period:

| Metric | Result | Evaluation Methodology |
| :--- | :--- | :--- |
| **Vehicle Detection Accuracy** | **~95%** | Evaluated on 500+ annotated video frames with diverse vehicles (sedans, SUVs, trucks, vans). A detection is counted as correct if IoU > 0.50 and the vehicle is tracked across the entry safe zone. False negatives primarily occurred with extreme occlusions or partial entries. |
| **License Plate Recognition** | **~80%** | Measured end-to-end (YOLO plate localization + Gemini OCR) across 350 valid plate samples. Evaluated under mixed lighting conditions (bright daylight, dusk, glare). Difficult cases (mud, angle > 45°, heavy glare) are flagged with `PENDING` status for one-click manual confirmation. |
| **Operational Throughput** | **60+ vehicles/day** | Sustained average logging throughput during peak operating hours without dropped frames or database lock contention (SQLite WAL mode). |
| **Inference Latency** | **~45 ms (YOLO) / ~800 ms (OCR)** | Vehicle detection runs at 20+ FPS locally on GPU. Gemini OCR calls are triggered asynchronously only upon validated line-crossing, preventing video stream bottlenecks. |

## Features

- Real-time vehicle detection using YOLOv11 with safe-zone geometry filtering
- License plate localization using a fine-tuned custom YOLO model
- High-accuracy license plate OCR with Google Gemini 2.0 Flash
- Human-in-the-loop staff confirmation for low-confidence or ambiguous reads
- Dual-camera architecture (front entry and rear exit) with automatic stream reconnection and video loop support
- Real-time WebSocket streaming to both Web Dashboard and Flutter Mobile App
- SQLite database with WAL (Write-Ahead Logging) mode for concurrent reads and writes
- Unified server architecture supporting both live RTSP cameras and simulated video playback via environment variables
- Automated test suite covering smoke imports, database operations, and geometric safe-zone calculations

## Quick Start

### 1. Automated Setup & Run (Windows)

Use the interactive demo script to launch everything together:

```cmd
run_demo.bat
```

Or on PowerShell:

```powershell
.\run_demo.ps1
```

This starts the unified backend server, opens `http://localhost:8001` in your browser, and provides keyboard options to launch the Flutter mobile app in Chrome (`flutter run -d chrome --web-port=5000`) and trigger simulated vehicle events.

### 2. Manual Start

```bash
git clone https://github.com/hyggg222/DKAI_DeployVer.git
cd DKAI_DeployVer

# Create virtual environment
python -m venv venv
# Windows: venv\Scripts\activate | Linux/macOS: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run setup wizard
python setup.py

# Run demo server
python ai_server_test.py

# Visit http://localhost:8001
```

## Tech Stack

- **Language**: Python 3.10+
- **Backend**: FastAPI (REST API), Python-SocketIO (Real-time WebSocket)
- **AI Models**:
  - **YOLOv11** (Object Detection: Vehicles)
  - **Custom Fine-tuned YOLO** (License Plate Detection)
  - **Google Gemini 2.0 Flash** (OCR & Context Verification)
- **Database**: SQLite (WAL Mode enabled for high concurrency)
- **Mobile App**: Flutter (Dart)

## Project Structure

```
DKAI_DeployVer/
├── ai_server.py              # Unified backend server (RTSP streams or test files, FastAPI + Socket.IO)
├── ai_server_test.py         # Test server wrapper (sets VIDEO_SOURCE=file and launches ai_server)
├── setup.py                  # Setup wizard and environment verification
├── requirements.txt          # Python dependencies
├── Dockerfile                # Container definition
├── docker-compose.yml        # Docker compose service definition
├── .env.example              # Environment configuration template
├── .gitignore               # Git ignore configuration
├── run_demo.bat              # Windows batch launcher (starts server + dashboard + mobile)
├── run_demo.ps1              # PowerShell interactive launcher
├── CHANGELOG.md              # Semantic release notes and changelog
├── LICENSE                   # MIT License
├── README.md                 # Project documentation
├── src/                     # Core AI and backend modules
│   ├── auto_trigger.py     # Vehicle tracking and line-crossing trigger logic
│   ├── camera_manager.py   # Dual-camera stream manager (RTSP & video looping)
│   ├── database.py         # SQLite logging and record management with WAL mode
│   ├── plate_detector.py   # License plate detector & Gemini OCR integration
│   └── vehicle_detector.py # Vehicle detection and bounding-box validation
├── weights/                 # Pre-trained model weights (committed in repo)
│   ├── license-plate-finetune-v1l.pt # License plate localization
│   ├── yolo11s.pt          # YOLOv11 vehicle detection
│   └── yolov8s.pt          # Alternative YOLOv8 vehicle detection
├── templates/              # Web dashboard templates
│   └── index.html          # Real-time monitoring dashboard (English interface)
├── static/                  # Static assets and placeholders
│   ├── no_car.jpg          # Placeholder image when vehicle crop is unavailable
│   └── no_plate.jpg        # Placeholder image when plate crop is unavailable
├── tests/                  # Automated test suite
│   ├── test_database.py    # Database CRUD tests
│   ├── test_server_endpoints.py # FastAPI route tests
│   ├── test_smoke.py       # Module import smoke tests
│   └── test_vehicle_detector_logic.py # Safe-zone and geometry algorithm tests
├── test_videos/            # Directory for user-provided test videos (.mp4)
└── mobile_flutter/         # Flutter mobile application
    ├── lib/                # Flutter/Dart source code
    ├── android/            # Android platform configuration
    ├── web/                # Flutter Web platform configuration
    └── pubspec.yaml        # Flutter package manifest
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/hyggg222/DKAI_DeployVer.git
cd DKAI_DeployVer
```

### 2. Set Up Python Environment

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

# Video Source (rtsp for live cameras, file for test videos)
VIDEO_SOURCE=rtsp

# RTSP Camera URLs (used when VIDEO_SOURCE=rtsp)
RTSP_FRONT=rtsp://username:password@camera_ip:554/stream1
RTSP_BACK=rtsp://username:password@camera_ip:554/stream2

# Test Video Paths (used when VIDEO_SOURCE=file)
TEST_VIDEO_FRONT=test_videos/front.mp4
TEST_VIDEO_BACK=test_videos/back.mp4

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8001

# Database Configuration
DATABASE_PATH=./registry.db
```

### 2. Get Google Gemini API Key

Obtain an API key from Google AI Studio and place it in your `.env` file as `GEMINI_API_KEY`.

### 3. RTSP Camera URLs

If you do not have physical RTSP cameras, you can use:
- **IP Webcam** apps (Android/iOS) to stream from your phone
- **USB cameras** with tools like `ffmpeg` or `mediamtx` to create RTSP streams
- **Test mode** with video files (`VIDEO_SOURCE=file`)

**RTSP URL Format Examples:**
```
rtsp://admin:password@192.168.1.100:554/stream1
rtsp://192.168.1.101:8554/cam1
rtsp://username:password@camera.example.com/live
```

## Usage

### Running the Test Server (Demo Mode)

Use this mode to verify the system without physical RTSP cameras.

Place your video files into the `test_videos/` directory:
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
- View real-time dual-camera feeds
- Monitor vehicle entry/exit logs and perform manual staff confirmations

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
- REST API: `http://your-server-ip:8001/api/history`
- WebSocket: `ws://your-server-ip:8001/socket.io`

### Stopping the Server

Press `Ctrl + C` in the terminal to gracefully shut down the server.

## Mobile App Setup

### 1. Prerequisites
- [Flutter SDK](https://docs.flutter.dev/get-started/install) (3.0+) installed and added to PATH.

### 2. Navigate to Mobile Directory

```bash
cd mobile_flutter
```

### 3. Install Dependencies

```bash
flutter pub get
```

### 4. Configure Server Connection

Edit `lib/config/api_config.dart` with your server IP:

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

### 5. Run the App

**For Android:**
```bash
flutter run
```

**For Web (Chrome):**
```bash
flutter run -d chrome --web-port=5000
```

**For a specific device:**
```bash
# List available devices
flutter devices

# Run on specific device
flutter run -d <device_id>
```

### 6. Build Release APK (Android)

```bash
flutter build apk --release
```

The APK will be located at `build/app/outputs/flutter-apk/app-release.apk`.

## API Documentation

### REST API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the web dashboard (`templates/index.html`) |
| `GET` | `/video_feed/{camera_id}` | Live MJPEG video feed (`front` or `back`) |
| `GET` | `/api/history` | Returns the recent vehicle log records |
| `POST` | `/api/ingest/confirm` | Staff confirmation for pending / low-confidence plate reads |
| `GET` | `/api/ingest/history` | Returns history of staff confirmations and review status |
| `POST` | `/api/test/trigger` | Triggers a simulated vehicle event (useful for end-to-end testing and demos) |

#### GET /api/history
Returns a list of recent vehicle records:
```json
[
  {
    "id": 1,
    "timestamp": "2026-11-12 14:30:00",
    "plate": "30A12345",
    "plate_number": "30A12345",
    "plate_url": "/images/captures/plate_1.jpg",
    "plate_image": "/images/captures/plate_1.jpg",
    "car_url": "/images/captures/car_1.jpg",
    "car_image": "/images/captures/car_1.jpg",
    "status": "APPROVED",
    "note": ""
  }
]
```

#### POST /api/ingest/confirm
Submits staff review for a vehicle log record:
```json
{
  "record_id": 1,
  "action": "APPROVED",
  "corrected_plate": "30A12345"
}
```

**Response:**
```json
{
  "success": true,
  "record_id": 1,
  "new_status": "APPROVED",
  "plate": "30A12345"
}
```

#### POST /api/test/trigger
Simulates a vehicle event:
```json
{
  "camera": "front",
  "plate_text": "30A12345"
}
```

### WebSocket Events

Connect to Socket.IO at `ws://<server-ip>:8001/socket.io`:

- **Event: `vehicle_detected`** (Server -> Client):
  Broadcast when a vehicle crosses the virtual trigger line and a license plate is recognized.
  ```json
  {
    "id": 1,
    "timestamp": "2026-11-12 14:30:00",
    "plate": "30A12345",
    "plate_image": "/images/captures/plate_1.jpg",
    "car_image": "/images/captures/car_1.jpg",
    "status": "APPROVED"
  }
  ```

- **Event: `plate_status_update`** (Server -> Client):
  Broadcast when staff approves or corrects a pending plate reading.
  ```json
  {
    "record_id": 1,
    "status": "APPROVED",
    "plate": "30A12345"
  }
  ```

## Testing

Run the automated test suite locally:

```bash
# Run Python unit tests
python -m unittest discover -s tests -v

# Run Flutter static analysis
cd mobile_flutter && flutter analyze
```

Continuous integration runs automatically on GitHub Actions via `.github/workflows/test.yml`.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Contact

For questions or support, please open an issue on GitHub.
