
import cv2
import time
import io
import os
import sys
import json # Added missing json import
import traceback # Added for debug
import socket
import asyncio
import threading
try:
    import torch  # Added for monkey-patch

    # MONKEY PATCH: Fix for PyTorch 2.6+ weights_only=True default
    _original_load = torch.load
    def safe_load(*args, **kwargs):
        if 'weights_only' not in kwargs:
            kwargs['weights_only'] = False
        return _original_load(*args, **kwargs)
    torch.load = safe_load
except Exception:
    torch = None

import sqlite3
import uvicorn
import socketio # Re-imported
import numpy as np
from datetime import datetime
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import List

# Import AI Modules
from src.plate_detector import PlateRecognizer
from src.vehicle_detector import CarDetector
from src.auto_trigger import AutoTriggerSystem 
from dotenv import load_dotenv

load_dotenv() 

# ================= CUSTOM LOOPING CAMERA CLASS =================
class LoopingCameraStream:
    def __init__(self, source, name="Camera"):
        self.source = source
        self.name = name
        self.stream = cv2.VideoCapture(self.source)
        self.fps = self.stream.get(cv2.CAP_PROP_FPS)
        if self.fps <= 0: self.fps = 30
        self.lock = threading.Lock()
        self.frame = np.zeros((360, 640, 3), dtype=np.uint8)
        self.stopped = False
        
        if not self.stream.isOpened():
            print(f"[{name}] ERROR: Could not open video file {source}")

    def start(self):
        t = threading.Thread(target=self.update, daemon=True)
        t.start()
        return self

    def update(self):
        while not self.stopped:
            grabbed, frame = self.stream.read()
            if not grabbed:
                # Stop at end of video (Run one time)
                print(f"[{self.name}] Video finished.")
                self.stopped = True
                continue
            
            # Simulate FPS
            time.sleep(1/self.fps)
            
            with self.lock:
                self.frame = frame

    def read(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def stop(self):
        self.stopped = True
        self.stream.release()

class LoopingDualCameraSystem:
    def __init__(self, src1, src2):
        self.cam_front = LoopingCameraStream(src1, "Front")
        self.cam_back = LoopingCameraStream(src2, "Back")
    
    def start(self):
        self.cam_front.start()
        self.cam_back.start()
        
    def stop(self):
        self.cam_front.stop()
        self.cam_back.stop()
        
    def get_frames(self):
        return self.cam_front.read(), self.cam_back.read()

# ================= CONFIGURATION =================
DB_NAME = "registry_test.db"
IMAGE_DIR = "images_test" 
os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(os.path.join(IMAGE_DIR, "captures"), exist_ok=True)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

PATH_PLATE = resource_path(os.path.join('weights', 'license-plate-finetune-v1l.pt'))
PATH_CAR   = resource_path(os.path.join('weights', 'yolo11s.pt'))
TRIGGER_LINE = [(50, 225), (590, 225)] 

# ================= APP SETUP =================
# SOCKET.IO SETUP
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
fastapi_app = FastAPI()
fastapi_app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Mount Socket.IO to FastAPI
app = socketio.ASGIApp(sio, fastapi_app)

# IMPORTANT: Mount as /static to match App expectation
fastapi_app.mount("/static", StaticFiles(directory=IMAGE_DIR), name="static")
# Mount outputs for Archive retrieval
fastapi_app.mount("/storage", StaticFiles(directory="outputs"), name="storage")

templates = Jinja2Templates(directory="templates")

@sio.event
async def connect(sid, environ):
    print(f"connect {sid}")
    query = environ.get('QUERY_STRING', '')
    print(f"Connection Query: {query}")

@sio.event
async def disconnect(sid):
    print(f"disconnect {sid}")

@sio.event
async def clear_session(sid, data):
    print(f">>> [SOCKET] Clearing Session Data (Requested by {sid})")
    global latest_payload
    latest_payload = None

# Global State
ai_running = True
current_session = {
    "state": "WATCHING",
    "start_time": 0,
    "plate_img": None,
    "car_img": None,
    "trigger_id": None
}
latest_payload = None # Store last result for late-joiners

cameras = None
plate_sys = None
vehicle_sys = None
trigger_sys = None
main_loop = None

# ... (Database functions omitted for brevity matching existing file) ...

@sio.event
async def connect(sid, environ):
    print(f"connect {sid}")
    query = environ.get('QUERY_STRING', '')
    print(f"Connection Query: {query}")
    
    # REPLAY FEATURE: RESTORED (Managed by clear_session)
    global latest_payload
    if latest_payload:
        print(f">>> [SOCKET] Replaying last payload to new client {sid}")
        # Emit all formats to be safe
        await sio.emit('notify_vehicle', latest_payload.get('payload_mobile_data', latest_payload['data']), room=sid)
        await sio.emit('review_request', latest_payload['data'], room=sid)
        await sio.emit('message', latest_payload, room=sid)
        await sio.emit('review_request_full', latest_payload.get('payload_mobile_data', latest_payload['data']), room=sid)

@sio.event
async def disconnect(sid):
    print(f"disconnect {sid}")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY, timestamp TEXT, plate TEXT, plate_url TEXT, car_url TEXT, status TEXT)")
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

# ================= AI LOGIC =================
@fastapi_app.on_event("startup")
async def startup():
    global main_loop, cameras, plate_sys, vehicle_sys, trigger_sys
    main_loop = asyncio.get_running_loop()
    init_db()
    
    # Initialize Models
    print(">>> [TEST] Loading Models (CPU FORCED)...")
    cameras = LoopingDualCameraSystem("test_videos/front.mp4", "test_videos/back.mp4")
    cameras.start()
    
    plate_sys = PlateRecognizer(PATH_PLATE, api_key=os.getenv("GEMINI_API_KEY"))
    vehicle_sys = CarDetector(PATH_CAR)
    trigger_sys = AutoTriggerSystem(PATH_CAR, TRIGGER_LINE, cooldown=5)
    
    # Force CPU
    if hasattr(plate_sys, 'plate_model'): plate_sys.plate_model.to('cpu')
    if hasattr(vehicle_sys, 'model'): vehicle_sys.model.to('cpu')
    if hasattr(trigger_sys, 'model'): trigger_sys.model.to('cpu')
    
    threading.Thread(target=ai_loop, daemon=True).start()
    print(">>> [TEST] Server Started.")

def ai_loop():
    global current_session
    while ai_running:
        try:
            f1, f2 = cameras.get_frames()
            if f1 is None: 
                time.sleep(0.1); continue
            
            # Use f1 for trigger
            f_trigger = cv2.resize(f1, (640, 360))
            is_trig, tid = trigger_sys.check(f_trigger)
            
            # State Machine
            if current_session["state"] == "WATCHING":
                # Passive Tracking for Visualization
                if f2 is not None:
                     vehicle_sys.detect(f2, capture_enabled=False)
                
                if is_trig:
                    print(f">>> [TEST] Trigger {tid}")
                    current_session.update({"state": "SCANNING", "start_time": time.time(), "trigger_id": tid, "plate_img": None, "car_img": None})
                    # Notify App/Web via Socket.IO
                    if main_loop: 
                        asyncio.run_coroutine_threadsafe(sio.emit('status_update', {'status': 'scanning', 'msg': f'Vehicle {tid}'}), main_loop)
            
            elif current_session["state"] == "SCANNING":
                # Capture
                p, _ = plate_sys.process(f1)
                c, car_id = vehicle_sys.detect(f2 if f2 is not None else f1) # Lấy cả car_id để log
                
                # --- THÊM LOG THÔNG BÁO TẠI ĐÂY ---
                if p is not None and current_session["plate_img"] is None:
                    print(f">>> [SESSION] Catched Plate")
                    current_session["plate_img"] = p

                if c is not None and current_session["car_img"] is None:
                    print(f">>> [SESSION] Catched Vehicle (ID: {car_id})")
                    current_session["car_img"] = c
                # ----------------------------------
                
                # Check Done
                if current_session["plate_img"] is not None and current_session["car_img"] is not None:
                    # Clone data for async processing
                    p_img = current_session["plate_img"].copy()
                    c_img = current_session["car_img"].copy()
                    t_id = current_session.get("trigger_id")
                    
                    # Schedule Async Task
                    if main_loop:
                        asyncio.run_coroutine_threadsafe(
                            finish_session_async("SUCCESS", p_img, c_img, t_id),
                            main_loop
                        )
                    
                    # Reset immediately to keep loop fast
                    current_session.update({"state": "WATCHING", "plate_img": None, "car_img": None})

                elif time.time() - current_session["start_time"] > 10:
                    # Timeout logic
                    p_img = current_session["plate_img"]
                    c_img = current_session["car_img"]
                    t_id = current_session.get("trigger_id")
                    
                    if main_loop:
                         asyncio.run_coroutine_threadsafe(
                            finish_session_async("TIMEOUT", p_img, c_img, t_id),
                            main_loop
                        )
                    current_session.update({"state": "WATCHING", "plate_img": None, "car_img": None})
            
            time.sleep(0.01)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)

async def finish_session_async(reason, p_img, c_img, trigger_id):
    print(f">>> [ASYNC] Processing Session: {reason}")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 1. Save Images
    p_url, c_url = "/static/no_plate.jpg", "/static/no_car.jpg"
    
    if p_img is not None:
        fn = f"plate_{ts}.jpg"
        cv2.imwrite(os.path.join(IMAGE_DIR, "captures", fn), p_img)
        p_url = f"/static/captures/{fn}"
        
    if c_img is not None:
        fn = f"car_{ts}.jpg"
        cv2.imwrite(os.path.join(IMAGE_DIR, "captures", fn), c_img)
        c_url = f"/static/captures/{fn}"

    # 2. AI VALIDATION (Gemini Async)
    gemini_result = None
    if p_img is not None and os.getenv("GEMINI_API_KEY"):
         # Non-blocking call
         gemini_result = await plate_sys.validate_event_gemini_async(p_img, c_img)
    
    # 3. Parse Decision
    plate = "UNKNOWN"
    status = "review_needed"
    alert_mode = "VIBRATE_AND_SOUND" # Default safe
    
    if gemini_result:
        plate = gemini_result.get("plate_text", "UNKNOWN")
        decision = gemini_result.get("decision", "NEED_HUMAN_CONFIRM")
        
        if decision == "AUTO_CONFIRM":
            status = "success" # or 'auto_confirmed'
            alert_mode = "SILENT_OK"
        
        # Override alert mode from AI if present
        if "notify" in gemini_result and "alert_mode" in gemini_result["notify"]:
             alert_mode = gemini_result["notify"]["alert_mode"]
             
        print(f">>> [AI DECISION] {decision} | Plate: {plate} | Mode: {alert_mode}")
    else:
        # Client Fallback if AI failed or no image
        plate = f"RAW-{trigger_id}"
    
    # 4. Save to DB
    new_id, str_time = add_record_db(plate, p_url, c_url, status=status)
    
    # 5. Build Payload for Mobile
    # HOST Logic (Keep existing logic)
    MOBILE_HOST = os.getenv("MOBILE_HOST_OVERRIDE")
    if not MOBILE_HOST:
         MOBILE_HOST = "http://10.0.2.2:8001" # Simpler fallback for now
    else:
         MOBILE_HOST = MOBILE_HOST.rstrip('/')

    full_p_url = f"{MOBILE_HOST}{p_url}"
    full_c_url = f"{MOBILE_HOST}{c_url}"
    
    payload_mobile = {
        "id": new_id,
        "timestamp": str_time,
        "plate": plate,
        "image_url": full_c_url,
        "plate_image_url": full_p_url,
        "status": status,
        "reason": reason,
        "notify": {
            "alert_mode": alert_mode,
            "message": f"Vehicle {plate}"
        }
    }

    print(f">>> [SOCKET] Emitting: {payload_mobile}")
    
    # 6. Emit (Await directly since we are in async)
    await sio.emit('notify_vehicle', payload_mobile)
    
    # Global Replay Cache
    global latest_payload
    latest_payload = {"data": payload_mobile, "payload_mobile_data": payload_mobile}
    
    await sio.emit('status_update', {'status': 'watching'})

# ================= APP API =================

@fastapi_app.post("/api/ingest/confirm")
async def api_ingest_confirm(
    plate: str = Form(...),
    timestamp: str = Form(...),
    image: UploadFile = File(None),
    plate_image: UploadFile = File(None)
):
    try:
        print(f">>> [API] Confirm Received: {plate} at {timestamp}")
        
        # 1. Prepare Directory: outputs/{plate}_{count}/
        safe_plate = "".join([c for c in plate if c.isalnum() or c in ('-','_')])
        base_output_dir = "outputs"
        os.makedirs(base_output_dir, exist_ok=True)

        # Find next count
        count = 1
        while True:
            folder_name = f"{safe_plate}_{count}"
            candidate_path = os.path.join(base_output_dir, folder_name)
            if not os.path.exists(candidate_path):
                save_dir = candidate_path
                break
            count += 1
        
        os.makedirs(save_dir, exist_ok=True)
        
        # Helper for processing
        async def process_and_save(upload_file, filename_suffix):
            if not upload_file: return None
            
            content = await upload_file.read()
            nparr = np.frombuffer(content, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None: return None
            
            # A. RESIZE (Standardize to 640x480)
            target_w, target_h = 640, 480
            img = cv2.resize(img, (target_w, target_h))
            
            # B. WATERMARK (Bottom-Right Timestamp)
            text = timestamp
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.8
            thickness = 2
            color = (0, 0, 255) # Red
            
            (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
            x = target_w - text_w - 10
            y = target_h - 10
            
            cv2.putText(img, text, (x, y), font, font_scale, color, thickness)
            
            # Save
            filename = f"{safe_plate}_{filename_suffix}.jpg"
            filepath = os.path.join(save_dir, filename)
            cv2.imwrite(filepath, img)
            return filename
            
        
        # Process Images
        car_fname = await process_and_save(image, "car")
        plate_fname = await process_and_save(plate_image, "plate")
        
        # Save Info JSON
        info = {
            "plate": plate,
            "count": count,
            "folder_name": os.path.basename(save_dir),
            "timestamp": timestamp,
            "car_image": car_fname,
            "plate_image": plate_fname
        }
        with open(os.path.join(save_dir, "info.json"), "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        # 3. ACK
        return {"status": "success", "message": f"Saved to {save_dir}"}

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@fastapi_app.get("/api/ingest/history")
async def api_ingest_history():
    base_output_dir = "outputs"
    if not os.path.exists(base_output_dir):
        return []
        
    history = []
    # Scan directories
    for entry in os.scandir(base_output_dir):
        if entry.is_dir():
            info_path = os.path.join(entry.path, "info.json")
            if os.path.exists(info_path):
                try:
                    with open(info_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        history.append(data)
                except Exception as e:
                    print(f"Error reading {info_path}: {e}")
    
    # Sort by timestamp descending (newest first)
    history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return history

# ================= WEB ROUTES =================
@fastapi_app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

# Note: WebSocket endpoint removed because we use Socket.IO (mounted at /socket.io automatically)

def gen_mjpeg(cam_id):
    while True:
        if cameras:
            f1, f2 = cameras.get_frames()
            
            # Chọn frame dựa trên cam_id
            if cam_id == 'front':
                frame = f1.copy() if f1 is not None else None
            else:
                # Cam sau (back)
                frame = f2.copy() if f2 is not None else None
            
            if frame is not None:
                # Calculate Scale Factor
                orig_h, orig_w = frame.shape[:2]
                frame = cv2.resize(frame, (640, 360))
                h, w = frame.shape[:2]
                scale_x = w / orig_w
                scale_y = h / orig_h

                if vehicle_sys:
                    sz = vehicle_sys.get_safe_zone(w, h) 
                    cv2.rectangle(frame, (sz[0], sz[1]), (sz[2], sz[3]), (0, 255, 0), 2)
                    cv2.putText(frame, "SAFE ZONE", (sz[0], sz[1]-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                if cam_id == 'front':
                    cv2.line(frame, TRIGGER_LINE[0], TRIGGER_LINE[1], (255, 0, 0), 2)
                    cv2.putText(frame, "TRIGGER LINE", (TRIGGER_LINE[0][0], TRIGGER_LINE[0][1]-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1)
                    

                    for trk in trigger_sys.latest_tracks:
                        x1, y1, x2, y2 = map(int, trk['box'])
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 1) 

                elif cam_id == 'back':
                    if vehicle_sys:
                        if hasattr(vehicle_sys, 'raw_detections'):
                            for (r_box, r_id) in vehicle_sys.raw_detections:
                                rcx, rcy, rw, rh = r_box
                                # Scale coordinates
                                rcx = rcx * scale_x
                                rcy = rcy * scale_y
                                rw  = rw  * scale_x
                                rh  = rh  * scale_y
                                
                                rx1, ry1 = int(rcx - rw/2), int(rcy - rh/2)
                                rx2, ry2 = int(rcx + rw/2), int(rcy + rh/2)
                                cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (0, 165, 255), 1) # Orange
                                cv2.putText(frame, f"{r_id}", (rx1, ry1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)

                   
                        if vehicle_sys.latest_box is not None:
                            bx1, by1, bx2, by2 = vehicle_sys.latest_box
                            # Scale coordinates (Note: latest_box is (x1, y1, x2, y2) in ORIG coords)
                            bx1 = int(bx1 * scale_x)
                            by1 = int(by1 * scale_y)
                            bx2 = int(bx2 * scale_x)
                            by2 = int(by2 * scale_y)
                            
                            cv2.rectangle(frame, (bx1, by1), (bx2, by2), (0, 0, 255), 3) 
                            cv2.putText(frame, f"CAPTURE: {vehicle_sys.latest_id}", (bx1, by1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

                ret, buf = cv2.imencode('.jpg', frame)
                if ret: yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
        time.sleep(0.04)

@fastapi_app.get("/video_feed/{cid}")
def video_feed(cid: str):
    return StreamingResponse(gen_mjpeg(cid), media_type="multipart/x-mixed-replace;boundary=frame")

@fastapi_app.get("/api/history")
def get_history():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM records ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    
    res = []
    for r in rows:
        res.append({
            "id": r["id"],
            "time": r["timestamp"],
            "plate_number": r["plate"],
            "plate_image": r["plate_url"],
            "car_image": r["car_url"],
            "status": r["status"],
            "visit_count": 1
        })
    return res

if __name__ == "__main__":
    print("="*60)
    print("   DK_AI TEST SERVER (SOCKET.IO RESTORED)")
    print("="*60)
    
    # PRINT AVAILABLE IPs
    print("\n[CONNECTIVITY INFO]")
    print("To connect the Mobile App, use one of these IP addresses:")
    
    try:
        host_name = socket.gethostname()
        ips = socket.gethostbyname_ex(host_name)[2]
        for ip in ips:
            if not ip.startswith("127."):
                print(f"  👉 http://{ip}:8001")
    except Exception as e:
        print(f"  (Could not list IPs: {e})")

    # Check Override
    override = os.getenv("MOBILE_HOST_OVERRIDE")
    if override:
        print(f"\n[NOTE] .env Override is ACTIVE: {override}")
    
    print("\n   Open http://localhost:8001 in browser")
    print("="*60)
    # Run 'app' (socketio wrapper) instead of 'fastapi_app'
    uvicorn.run(app, host="0.0.0.0", port=8001)
