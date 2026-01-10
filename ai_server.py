import cv2
import time
import io
import os
import sys
import socket
import asyncio
import threading
import sqlite3
import uvicorn
import socketio
import numpy as np
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import AI Modules (Relative to this file)
from src.camera_manager import DualCameraSystem
from src.plate_detector import PlateRecognizer
from src.vehicle_detector import CarDetector
from src.auto_trigger import AutoTriggerSystem 
from dotenv import load_dotenv

load_dotenv() 

# ================= CONFIGURATION =================
DB_NAME = "registry.db"
IMAGE_DIR = "images"
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(os.path.join(IMAGE_DIR, "captures"), exist_ok=True)
os.makedirs(os.path.join(IMAGE_DIR, "confirmed"), exist_ok=True)

# Determine resource path for PyInstaller
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

PATH_PLATE = resource_path(os.path.join('weights', 'license-plate-finetune-v1l.pt'))
PATH_CAR   = resource_path(os.path.join('weights', 'yolo11s.pt'))
TRIGGER_LINE = [(50, 225), (590, 225)] 

# Local IP Helper
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]; s.close()
        return ip
    except: return "127.0.0.1"

# ================= DATABASE (SQLite WAL) =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA journal_mode=WAL;") 
    conn.execute("PRAGMA synchronous=NORMAL;")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS records
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  plate_number TEXT,
                  plate_image TEXT,
                  car_image TEXT,
                  status TEXT, 
                  note TEXT)''')
    conn.commit()
    conn.close()

def add_record_db(plate_num, plate_path, car_path, status="review_needed"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO records (timestamp, plate_number, plate_image, car_image, status, note) VALUES (?, ?, ?, ?, ?, ?)",
              (ts, plate_num, plate_path, car_path, status, ''))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id, ts

def get_recent_records(limit=50):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM records ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(ix) for ix in rows]

# ================= FASTAPI & SOCKET.IO =================
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
fastapi_app = FastAPI()
app = socketio.ASGIApp(sio, fastapi_app)

# Serve Images
fastapi_app.mount("/images", StaticFiles(directory=IMAGE_DIR), name="images")

# Global State for AI
ai_system_running = True
current_session = {
    "state": "WATCHING",
    "start_time": 0,
    "plate_img": None,
    "car_img": None,
    "trigger_id": None
}
# AI Instances (Lazy Load)
cameras = None
plate_sys = None
vehicle_sys = None
trigger_sys = None

# Global Loop Capture
main_loop = None

@fastapi_app.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()
    init_db()
    print(">>> [SERVER] Database Initialized (WAL Mode).")
    threading.Thread(target=ai_processing_loop, daemon=True).start()

# ...

def emit_vehicle_event(plate_text, car_img, plate_img):
    """Save Temp Images & Emit Socket Event"""
    try:
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Save to Disk (Temp)
        car_url = ""
        if car_img is not None:
            fn = f"temp_{ts_str}_car.jpg"
            cv2.imwrite(os.path.join(IMAGE_DIR, "captures", fn), car_img)
            car_url = f"/images/captures/{fn}"
            
        plate_url = ""
        if plate_img is not None:
            fn = f"temp_{ts_str}_plate.jpg"
            cv2.imwrite(os.path.join(IMAGE_DIR, "captures", fn), plate_img)
            plate_url = f"/images/captures/{fn}"

        # 2. Build Payload
        payload = {
            "plate": plate_text,
            "image_url": car_url,
            "plate_image_url": plate_url,
            "timestamp": datetime.now().isoformat()
        }
        
        # 3. Emit via Main Loop
        if main_loop:
            asyncio.run_coroutine_threadsafe(sio.emit('notify_vehicle', payload), main_loop)
            print(f">>> [AI] 📡 Sent Event: {plate_text}")
        else:
            print(">>> [AI WARN] Main Loop not ready, skipping emit.")
        
    except Exception as e:
        print(f">>> [AI ERROR] Emit failed: {e}")

def process_session_result(reason):
    global current_session
    print(f">>> [AI] Finish Session: {reason}")
    
    # OCR Logic
    final_plate = "UNKNOWN"
    if current_session["plate_img"] is not None:
        # NOTE: Using Mock OCR if Gemini not set, or real if set
        # For standalone demo, we often skip external API or assume key present
        if os.getenv("GEMINI_API_KEY"):
            res = plate_sys.recognize_gemini(current_session["plate_img"])
            if res: final_plate = res
        else:
            final_plate = f"AUTO-{current_session['trigger_id']}"
            
    emit_vehicle_event(final_plate, current_session["car_img"], current_session["plate_img"])
    
    # Reset
    current_session["plate_img"] = None
    current_session["car_img"] = None
    current_session["state"] = "WATCHING"

def ai_processing_loop():
    global cameras, plate_sys, vehicle_sys, trigger_sys, current_session
    
    # Initialize AI Components
    print(">>> [AI] Loading Models...")
    # NOTE: Using Camera URL from ENV or defaulting to 0/1 for local testing if needed
    src1 = os.getenv("RTSP_CAMERA_URL")
    src2 = os.getenv("RTSP_CAMERA_URL")
    
    cameras = DualCameraSystem(src1, src2)
    trigger_sys = AutoTriggerSystem(model_path=PATH_CAR, line_points=TRIGGER_LINE, cooldown=5)
    plate_sys = PlateRecognizer(plate_model_path=PATH_PLATE, api_key=os.getenv("GEMINI_API_KEY")) 
    vehicle_sys = CarDetector(model_path=PATH_CAR)
    
    cameras.start()
    print(">>> [AI] Loop Started. Waiting for vehicles...")
    
    while ai_system_running:
        try:
            frame_front, frame_back = cameras.get_frames()
            if frame_front is None:
                time.sleep(0.01); continue
            
            if frame_back is None: frame_back = frame_front.copy() # Fallback

            # Trigger Check
            frame_trigger = cv2.resize(frame_front, (640, 360))
            is_triggered, t_id = trigger_sys.check(frame_trigger)

            # State Machine
            if current_session["state"] == "WATCHING":
                if is_triggered:
                    print(f">>> [AI] 🚀 Trigger ID: {t_id}")
                    current_session["state"] = "SCANNING"
                    current_session["start_time"] = time.time()
                    current_session["trigger_id"] = t_id
                    current_session["plate_img"] = None
                    current_session["car_img"] = None
            
            elif current_session["state"] == "SCANNING":
                # 1. Capture Plate
                p_img, _ = plate_sys.process(frame_front)
                if p_img is not None: current_session["plate_img"] = p_img
                
                # 2. Capture Car
                c_img, _ = vehicle_sys.detect(frame_back)
                if c_img is not None: current_session["car_img"] = c_img
                
                # 3. Check Finish
                has_both = current_session["plate_img"] is not None and current_session["car_img"] is not None
                is_timeout = (time.time() - current_session["start_time"]) > 10.0
                
                if has_both: process_session_result("SUCCESS")
                elif is_timeout: process_session_result("TIMEOUT")
            
            time.sleep(0.01)
            
        except Exception as e:
            print(f">>> [AIFATAL] {e}")
            time.sleep(1)

    cameras.stop()

if __name__ == "__main__":
    ip = get_local_ip()
    print("="*50)
    print(f"   DK_AI STANDALONE SERVER")
    print(f"   IP Address: {ip}")
    print(f"   API Port:   8000")
    print("="*50)
    # Run Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
