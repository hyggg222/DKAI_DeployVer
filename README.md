# DK_AI Standalone System

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flutter](https://img.shields.io/badge/Flutter-3.0+-02569B.svg?logo=flutter)](https://flutter.dev/)

A comprehensive AI-driven Vehicle Entry/Exit Management System with real-time license plate detection using YOLOv11 and Google Gemini OCR.

## ⚡ Quick Start

```bash
# 1. Clone and navigate
git clone https://github.com/hyggg222/DKAI_DeployVer.git
cd DKAI_DeployVer

# 2. Run setup wizard
python setup.py

# 3. Configure .env file
# (Setup wizard does this, but manual option below)
# cp .env.example .env

# 4. Test the system
python ai_server_test.py

# 5. Open browser
# Visit http://localhost:8001
```

## 🛠 Tech Stack
- **Language**: Python 3.10+
- **Backend**: FastAPI (Rest API), Python-SocketIO (Real-time)
- **AI Models**:
    - **YOLOv11** (Object Detection: Vehicles)
    - **Custom Finetuned YOLO** (License Plate Detection)
    - **Google Gemini 2.0 Flash Exp** (OCR & Context Verification)
- **Database**: SQLite (WAL Mode enabled for high concurrency)
- **Mobile App**: Flutter (Dart)

## 📂 Project Structure
- `ai_server.py`: **Main Production Server** (Uses RTSP Cameras).
- `ai_server_test.py`: **Test Server** (Uses looped video files for demo/debug).
- `setup.py`: **Setup Wizard** to initialize the project easier.
- `test_videos/`: Contains sample footage (`front.mp4`, `back.mp4`) for testing.
- `mobile_flutter/`: Source code for the mobile client.
- `src/`: Core AI modules.
- `weights/`: Pre-trained model weights.

## 🚀 Installation & Usage

### 1. Prerequisites
Install dependencies:
```bash
pip install -r requirements.txt
```

**Recommended**: Run the setup wizard to create directories, configs, and check dependencies:
```bash
python setup.py
```

### 2. Running the Test Server (Demo Mode)
Use this mode to verify the system logic without real cameras. It uses videos from `test_videos/`.
```bash
python ai_server_test.py
```
- Open `http://localhost:8001` to view testing status.
- The server simulates vehicles triggering the system.

### 3. Running the Production Server
Use this for real-world deployment with RTSP cameras.
```bash
python ai_server.py
```
- **Configuration**:
    - The server will check for `.env` file for `RTSP_FRONT` and `RTSP_BACK`.
    - If not found, it will **prompt you to type the RTSP URLs** (or Camera IDs) in the console at startup.

### 4. Running the Mobile App
navigate to `mobile_flutter` folder and run:
```bash
flutter pub get
flutter run
```
- Ensure your phone/emulator is on the same network.
- Enter the computer's IP address (displayed in the server console) when prompted by the app.
- Check `lib/config/api_config.dart` if you need to hardcode the IP.

### 5. Running with Docker (Optional)
```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## 📸 Screenshots

*(Add your screenshots in docs/images/ folder)*
### Web Interface
<img src="docs/images/dashboard.png" alt="Web Dashboard" width="600">

### Mobile App
<img src="docs/images/mobile-app.png" alt="Mobile App" width="300">

## 🔐 Configuration
- **API Keys**: Create a `.env` file (use `.env.example` as a template) to set `GEMINI_API_KEY`.
- **Ignore Rules**: Large files (`*.mp4`, `*.db`) are ignored by git to keep the repo light.

## ❓ FAQ

**Q: Do I need a GPU to run this?**
A: No, but a GPU (NVIDIA with CUDA) significantly improves performance. The system works on CPU-only systems with reduced frame rates.

**Q: Can I use USB webcams instead of RTSP cameras?**
A: Yes! Use camera ID (0, 1, etc.) in the .env file or when prompted.

**Q: How accurate is the license plate recognition?**
A: Accuracy depends on lighting, camera quality, and plate visibility. Typically 85-95% in good conditions.

**Q: Can I use this commercially?**
A: Yes, the project is MIT licensed.

**Q: Does this work with non-English license plates?**
A: Yes, Google Gemini supports multiple languages and character sets.
