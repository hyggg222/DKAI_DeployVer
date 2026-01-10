# DK_AI Standalone System

A comprehensive AI-driven Vehicle Entry/Exit Management System.

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

## 🚀 Getting Started

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

## 🔐 Configuration
- **API Keys**: Create a `.env` file (use `.env.example` as a template) to set `GEMINI_API_KEY`.
- **Ignore Rules**: Large files (`*.mp4`, `*.db`) are ignored by git to keep the repo light.
