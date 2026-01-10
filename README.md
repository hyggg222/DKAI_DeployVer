# DK_AI Standalone System

A comprehensive AI-driven Vehicle Entry/Exit Management System with real-time license plate detection, recognition, and automated gate control.

## 📋 Table of Contents

- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [System Requirements](#-system-requirements)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Mobile App Setup](#-mobile-app-setup)
- [API Documentation](#-api-documentation)
- [Troubleshooting](#-troubleshooting)
- [License](#-license)

## ✨ Features

- Real-time vehicle detection using YOLOv11
- License plate detection with custom fine-tuned YOLO model
- OCR and context verification with Google Gemini 2.0 Flash
- Dual camera support (entry and exit)
- Real-time WebSocket communication
- Mobile app for remote monitoring
- SQLite database with WAL mode for high concurrency
- Support for both RTSP cameras and test video files

## 🛠 Tech Stack

- **Language**: Python 3.10+
- **Backend**: FastAPI (REST API), Python-SocketIO (Real-time WebSocket)
- **AI Models**:
  - **YOLOv11** (Object Detection: Vehicles)
  - **Custom Fine-tuned YOLO** (License Plate Detection)
  - **Google Gemini 2.0 Flash Exp** (OCR & Context Verification)
- **Database**: SQLite (WAL Mode enabled for high concurrency)
- **Mobile App**: Flutter (Dart)

## 💻 System Requirements

### Minimum Requirements
- **OS**: Windows 10/11, Ubuntu 20.04+, or macOS 11+
- **CPU**: Intel Core i5 (8th gen) or equivalent
- **RAM**: 8GB
- **Storage**: 5GB free space
- **Python**: 3.10 or higher

### Recommended Requirements
- **CPU**: Intel Core i7/i9 or AMD Ryzen 7/9
- **GPU**: NVIDIA GPU with CUDA support (GTX 1660 or better)
- **RAM**: 16GB or more
- **Storage**: 10GB+ SSD

### For Mobile App Development
- **Flutter SDK**: 3.0+
- **Dart SDK**: 3.0+
- **Android Studio** or **Xcode** (for iOS)

## 📂 Project Structure

```
DKAI_DeployVer/
├── ai_server.py              # Main production server (RTSP cameras)
├── ai_server_test.py         # Test server (video files)
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore               # Git ignore rules
├── LICENSE                  # MIT License
├── README.md                # This file
├── src/                     # Core AI modules
│   ├── vehicle_detector.py # Vehicle detection logic
│   ├── plate_detector.py   # License plate detection
│   └── ocr_processor.py    # OCR with Gemini
├── weights/                 # Pre-trained model weights
│   ├── yolo11n.pt          # YOLOv11 vehicle detection
│   └── best.pt             # Custom license plate model
├── templates/              # HTML templates (if any)
├── test_videos/            # Sample footage for testing
│   ├── front.mp4          # Front camera simulation
│   └── back.mp4           # Back camera simulation
└── mobile_flutter/         # Flutter mobile app
    ├── lib/               # Dart source code
    ├── android/          # Android config
    ├── ios/             # iOS config
    └── pubspec.yaml     # Flutter dependencies
```

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/hyggg222/DKAI_DeployVer.git
cd DKAI_DeployVer
```

### 2. Set Up Python Environment

It's recommended to use a virtual environment:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Download Model Weights

The model weights are not included in the repository due to file size. Download them from the following sources:

#### YOLOv11 Weights
```bash
# Download YOLOv11n model
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolo11n.pt -O weights/yolo11n.pt
```

Or manually download from: [Ultralytics YOLO Models](https://github.com/ultralytics/ultralytics)

#### Custom License Plate Detection Model
Contact the repository owner or refer to the model training documentation for the custom `best.pt` model.

**Note**: Ensure both files are placed in the `weights/` directory:
- `weights/yolo11n.pt`
- `weights/best.pt`

## ⚙️ Configuration

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

# Optional: Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8001

# Optional: Database Configuration
DATABASE_PATH=./vehicle_logs.db
```

### 2. Get Google Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the API key and paste it in your `.env` file

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

## 🎮 Usage

### Running the Test Server (Demo Mode)

Use this mode to verify the system without real cameras. It uses videos from `test_videos/`.

```bash
python ai_server_test.py
```

**What happens:**
- Server starts on `http://localhost:8001`
- Automatically loops `front.mp4` and `back.mp4` from `test_videos/`
- Simulates vehicle detection and plate recognition
- Perfect for testing, demos, and development

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

## 📱 Mobile App Setup

### 1. Install Flutter

Follow the official Flutter installation guide: [flutter.dev](https://flutter.dev/docs/get-started/install)

Verify installation:
```bash
flutter doctor
```

### 2. Navigate to Mobile Directory

```bash
cd mobile_flutter
```

### 3. Install Dependencies

```bash
flutter pub get
```

### 4. Configure Server Connection

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

## 📡 API Documentation

### REST API Endpoints

#### Get Vehicle Logs
```http
GET /api/logs
```

**Response:**
```json
{
  "logs": [
    {
      "id": 1,
      "plate_number": "ABC1234",
      "timestamp": "2025-01-10 14:30:00",
      "camera": "front",
      "confidence": 0.95
    }
  ]
}
```

#### Get System Status
```http
GET /api/status
```

**Response:**
```json
{
  "status": "online",
  "cameras": {
    "front": "connected",
    "back": "connected"
  },
  "uptime": 3600
}
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

## 🔧 Troubleshooting

### Common Issues

#### 1. Import Errors or Missing Dependencies
```bash
# Reinstall all dependencies
pip install -r requirements.txt --force-reinstall
```

#### 2. CUDA/GPU Not Detected
```bash
# Verify PyTorch CUDA installation
python -c "import torch; print(torch.cuda.is_available())"

# If False, reinstall PyTorch with CUDA support
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

#### 3. Camera Connection Failed
- Verify RTSP URL is correct
- Check camera is accessible on network: `ping camera_ip`
- Test RTSP stream with VLC Media Player
- Ensure firewall allows RTSP traffic (port 554)

#### 4. Gemini API Errors
```
Error: Invalid API Key
```
**Solution**: 
- Verify your `GEMINI_API_KEY` in `.env`
- Check if the API key is active in Google AI Studio
- Ensure you haven't exceeded API quota

#### 5. Database Locked Error
```
sqlite3.OperationalError: database is locked
```
**Solution**: 
- The server automatically uses WAL mode
- If issue persists, delete `vehicle_logs.db` and restart

#### 6. Port Already in Use
```
Error: [Errno 48] Address already in use
```
**Solution**:
```bash
# Find process using port 8001
# Windows:
netstat -ano | findstr :8001
# macOS/Linux:
lsof -i :8001

# Kill the process or change port in code
```

#### 7. Mobile App Cannot Connect
- Ensure phone and server are on the same network
- Check firewall settings allow port 8001
- Verify server IP address in app configuration
- Test server accessibility: `http://server-ip:8001` in phone browser

### Performance Optimization

#### For Low-End Hardware
- Use smaller YOLO model (yolo11n instead of yolo11l)
- Reduce frame processing rate in code
- Process every 2nd or 3rd frame instead of all frames

#### For Better Accuracy
- Upgrade to larger YOLO model (yolo11l or yolo11x)
- Increase camera resolution
- Improve lighting conditions
- Fine-tune detection confidence thresholds

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Note**: This system is designed for controlled environments. Ensure compliance with local privacy and surveillance regulations when deploying in production.
