
import cv2
import time
import io
import os
import sys
import json
import traceback
import socket
import asyncio
import threading
import torch

# MONKEY PATCH: Fix for PyTorch 2.6+ weights_only=True default
_original_load = torch.load
def safe_load(*args, **kwargs):
    if 'weights_only' not in kwargs:
        kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = safe_load

import sqlite3
import uvicorn
import socketio
import numpy as np
from datetime import datetime
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# Import AI Modules
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

# Helper for Resource Path
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

PATH_PLATE = resource_path(os.path.join('weights', 'license-plate-finetune-v1l.pt'))
PATH_CAR   = resource_path(os.path.join('weights', 'yolo11s.pt'))
TRIGGER_LINE = [(50, 225), (590, 225)] 

# ================= FASTAPI & SOCKET.IO =================
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
fastapi_app = FastAPI()
fastapi_app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app = socketio.ASGIApp(sio, fastapi_app)

# Mount Static Files
fastapi_app.mount("/images", StaticFiles(directory=IMAGE_DIR), name="images")
# Compatibility with test server paths (it used /static)
fastapi_app.mount("/static", StaticFiles(directory=IMAGE_DIR), name="static")

templates = Jinja2Templates(directory="templates")

# ================= GLOBAL STATE =================
ai_running = True
current_session = {
    "state": "WATCHING",
    "start_time": 0,
    "plate_img": None,
    "car_img": None,
    "trigger_id": None
}
latest_payload = None

# AI Instances
cameras = None
plate_sys = None
vehicle_sys = None
trigger_sys = None
main_loop = None

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    # Unified Schema
    conn.execute("CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY, timestamp TEXT, plate TEXT, plate_url TEXT, car_url TEXT, status TEXT, note TEXT)")
    conn.close()

def add_record_db(plate, plate_url, car_url, status="review_needed"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO records (timestamp, plate, plate_url, car_url, status) VALUES (?, ?, ?, ?, ?)",
              (ts, plate, plate_url, car_url, status))
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id, ts

# ================= SOCKET EVENTS =================
@sio.event
async def connect(sid, environ):
    print(f"connect {sid}")
    # Replay last event if available
    global latest_payload
    if latest_payload:
        print(f">>> [SOCKET] Replaying last payload to {sid}")
        await sio.emit('notify_vehicle', latest_payload, room=sid)

@sio.event
async def disconnect(sid):
    print(f"disconnect {sid}")

# ================= AI LOGIC =================

@fastapi_app.on_event("startup")
async def startup_event():
    global main_loop, cameras, plate_sys, vehicle_sys, trigger_sys
    main_loop = asyncio.get_running_loop()
    init_db()
    
    # 1. CAMERA SELECTION
    # Check Environment Variables first
    src1 = os.getenv("RTSP_FRONT")
    src2 = os.getenv("RTSP_BACK")
    
    # If not found, ASK THE USER
    if not src1 or not src2:
        print("\n" + "="*50)
        print("   CAMERA CONFIGURATION REQUIRED")
        print("="*50)
        print("Please enter the RTSP URL or Cams ID (0, 1...) for your cameras.")
        
        if not src1:
            src1_input = input("INPUT: Front Camera URL/ID (default 0): ").strip()
            src1 = src1_input if src1_input else "0"
            # Try convert to int if it looks like a number
            if src1.isdigit(): src1 = int(src1)
            
        if not src2:
            src2_input = input("INPUT: Back Camera URL/ID (default 1): ").strip()
            src2 = src2_input if src2_input else "1"
            if isinstance(src2, str) and src2.isdigit(): src2 = int(src2)
            
        print("-"*50 + "\n")

    print(f">>> [AI] Initializing Cameras: Front={src1}, Back={src2}")
    
    cameras = DualCameraSystem(src1, src2)
    
    print(">>> [AI] Loading AI Models...")
    plate_sys = PlateRecognizer(plate_model_path=PATH_PLATE, api_key=os.getenv("GEMINI_API_KEY"))
    vehicle_sys = CarDetector(model_path=PATH_CAR)
    trigger_sys = AutoTriggerSystem(model_path=PATH_CAR, line_points=TRIGGER_LINE, cooldown=5)

    cameras.start()
    print(">>> [AI] System Ready. Starting Loop...")
    
    threading.Thread(target=ai_loop, daemon=True).start()

def ai_loop():
    global current_session
    while ai_running:
        try:
            # Get latest frames
            f1, f2 = cameras.get_frames()
            
            # If front camera is dead, wait
            if f1 is None: 
                time.sleep(0.01); continue
            
            # Fallback for back camera if missing
            if f2 is None: f2 = f1.copy()
            
            # 1. Trigger Check (Front Cam)
            f_trigger = cv2.resize(f1, (640, 360))
            is_trig, tid = trigger_sys.check(f_trigger)
            
            # 2. State Machine
            if current_session["state"] == "WATCHING":
                # Passive detect on back cam for visualization/warmup (optional)
                # vehicle_sys.detect(f2, capture_enabled=False)
                
                if is_trig:
                    print(f">>> [AI] 🚀 Trigger Activated: {tid}")
                    current_session.update({
                        "state": "SCANNING",
                        "start_time": time.time(),
                        "trigger_id": tid,
                        "plate_img": None,
                        "car_img": None
                    })
                    # Notify Watchers
                    if main_loop: 
                        asyncio.run_coroutine_threadsafe(
                            sio.emit('status_update', {'status': 'scanning', 'msg': f'Vehicle {tid}'}),
                            main_loop
                        )

            elif current_session["state"] == "SCANNING":
                # A. Capture Plate (Front)
                p, _ = plate_sys.process(f1)
                
                # B. Capture Car (Back)
                c, car_id = vehicle_sys.detect(f2)
                
                # Log Success
                if p is not None and current_session["plate_img"] is None:
                    print(f">>> [SESSION] ✅ Captured PLATE")
                    current_session["plate_img"] = p

                if c is not None and current_session["car_img"] is None:
                    print(f">>> [SESSION] ✅ Captured CAR (ID: {car_id})")
                    current_session["car_img"] = c
                
                # Check Completion
                has_images = current_session["plate_img"] is not None and current_session["car_img"] is not None
                is_timeout = (time.time() - current_session["start_time"]) > 10.0
                
                if has_images or is_timeout:
                    reason = "SUCCESS" if has_images else "TIMEOUT"
                    
                    # Prepare data for async
                    p_img = current_session["plate_img"]
                    c_img = current_session["car_img"]
                    t_id = current_session.get("trigger_id")
                    
                    # Offload to Async
                    if main_loop:
                        asyncio.run_coroutine_threadsafe(
                            finish_session_async(reason, p_img, c_img, t_id),
                            main_loop
                        )
                    
                    # Reset
                    current_session.update({"state": "WATCHING", "plate_img": None, "car_img": None})
            
            time.sleep(0.01)
            
        except Exception as e:
            print(f">>> [AI ERROR] {e}")
            traceback.print_exc()
            time.sleep(1)

    cameras.stop()

async def finish_session_async(reason, p_img, c_img, trigger_id):
    print(f">>> [ASYNC] Finalizing Session: {reason}")
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Save Images
    p_url, c_url = "", ""
    # Using /images/captures which maps to IMAGE_DIR/captures
    
    if p_img is not None:
        fn = f"plate_{ts_str}.jpg"
        cv2.imwrite(os.path.join(IMAGE_DIR, "captures", fn), p_img)
        p_url = f"/images/captures/{fn}"
        
    if c_img is not None:
        fn = f"car_{ts_str}.jpg"
        cv2.imwrite(os.path.join(IMAGE_DIR, "captures", fn), c_img)
        c_url = f"/images/captures/{fn}"

    # 2. AI Validation (Gemini)
    gemini_result = None
    if p_img is not None and os.getenv("GEMINI_API_KEY"):
         # Using the async validator
         gemini_result = await plate_sys.validate_event_gemini_async(p_img, c_img)
    
    # 3. Decision Logic
    plate_text = "UNKNOWN"
    status = "review_needed"
    alert_mode = "VIBRATE_AND_SOUND" # Default
    
    if gemini_result:
        plate_text = gemini_result.get("plate_text", "UNKNOWN")
        decision = gemini_result.get("decision", "NEED_HUMAN_CONFIRM")
        
        if decision == "AUTO_CONFIRM":
            status = "success"
            alert_mode = "SILENT_OK"
        
        if "notify" in gemini_result and "alert_mode" in gemini_result["notify"]:
             alert_mode = gemini_result["notify"]["alert_mode"]
             
        print(f">>> [GEMINI] {decision} | Plate: {plate_text}")
    else:
        # Fallback
        plate_text = f"RAW-{trigger_id}"
    
    # 4. Save to DB
    new_id, str_time = add_record_db(plate_text, p_url, c_url, status=status)
    
    # 5. Emit to Client
    # Build complete URL if needed (Mobile app often needs full IP)
    # But simple path works if relative or handled by app. 
    # Logic from test file adds Host:
    MOBILE_HOST = os.getenv("MOBILE_HOST_OVERRIDE", "")
    # If using relative paths in app, we can omit host. But let's keep it clean:
    # If p_url starts with /, it's relative.
    
    payload = {
        "id": new_id,
        "timestamp": str_time,
        "plate": plate_text,
        "image_url": p_url, # Mobile app might expect 'image_url' to be car or plate depending on version
        "plate_image_url": c_url, # Swapped? Let's keep consistency with test file:
                                  # Test file: image_url -> CAR, plate_image_url -> PLATE
                                  # Let's match that.
        "status": status,
        "reason": reason,
        "notify": {
            "alert_mode": alert_mode,
            "message": f"Vehicle {plate_text}"
        },
        # Fix URL assignment
        "image_url": c_url if c_url else "",
        "plate_image_url": p_url if p_url else ""
    }

    # If Host Override is active, prepend it
    if MOBILE_HOST:
        if payload["image_url"]: payload["image_url"] = f"{MOBILE_HOST}{payload['image_url']}"
        if payload["plate_image_url"]: payload["plate_image_url"] = f"{MOBILE_HOST}{payload['plate_image_url']}"

    print(f">>> [SOCKET] Emitting: {payload}")
    await sio.emit('notify_vehicle', payload)
    
    global latest_payload
    latest_payload = payload
    
    await sio.emit('status_update', {'status': 'watching'})


# ================= VIDEO FEED GEN =================
def gen_mjpeg(cam_id):
    while True:
        if cameras:
            f1, f2 = cameras.get_frames()
            
            frame = None
            if cam_id == 'front': frame = f1
            elif cam_id == 'back': frame = f2
            
            if frame is not None:
                # Resize for bandwidth
                frame = cv2.resize(frame, (640, 360))
                
                # --- DRAWING (Optional) ---
                # Draw trigger line on front
                if cam_id == 'front':
                    cv2.line(frame, TRIGGER_LINE[0], TRIGGER_LINE[1], (255, 0, 0), 2)
                    
                ret, buf = cv2.imencode('.jpg', frame)
                if ret: yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
        
        time.sleep(0.04) # ~25 FPS

# ================= API ROUTES =================
@fastapi_app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@fastapi_app.get("/video_feed/{cid}")
def video_feed(cid: str):
    return StreamingResponse(gen_mjpeg(cid), media_type="multipart/x-mixed-replace;boundary=frame")

@fastapi_app.get("/api/history")
def get_history():
    return get_recent_records(50)

def get_recent_records(limit=50):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM records ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(ix) for ix in rows]

# ================= MAIN =================
if __name__ == "__main__":
    # Local IP Helper
    def get_local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]; s.close()
            return ip
        except: return "127.0.0.1"

    ip = get_local_ip()
    print("="*60)
    print(f"   DK_AI STANDALONE SERVER")
    print(f"   Status:  Ready")
    print(f"   IP:      {ip}")
    print(f"   Port:    8000")
    print("="*60)
    print("NOTE: If camera URLs are not in .env, you can type them now.")
    
    # Run Uvicorn
    # Use 'app' (socketio) as entry point
    uvicorn.run(app, host="0.0.0.0", port=8000)

