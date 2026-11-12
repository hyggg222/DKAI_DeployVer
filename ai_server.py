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
import sqlite3
import uvicorn
import socketio
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates

# MONKEY PATCH: Fix for PyTorch 2.6+ weights_only=True default
try:
    import torch
    _original_load = torch.load
    def safe_load(*args, **kwargs):
        if 'weights_only' not in kwargs:
            kwargs['weights_only'] = False
        return _original_load(*args, **kwargs)
    torch.load = safe_load
except Exception:
    torch = None

# Import AI Modules
from src.camera_manager import DualCameraSystem
from src.plate_detector import PlateRecognizer
from src.vehicle_detector import CarDetector
from src.auto_trigger import AutoTriggerSystem

load_dotenv()

# ================= CONFIGURATION =================
DB_NAME = os.getenv("DATABASE_PATH", "registry.db")
IMAGE_DIR = "images"
STATIC_DIR = "static"
OUTPUT_DIR = "outputs"

os.makedirs(IMAGE_DIR, exist_ok=True)
os.makedirs(os.path.join(IMAGE_DIR, "captures"), exist_ok=True)
os.makedirs(os.path.join(IMAGE_DIR, "confirmed"), exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

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
fastapi_app = FastAPI(title="DKAI Monitoring Server", version="1.1.0")
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)
app = socketio.ASGIApp(sio, fastapi_app)

# Mount Static Files
fastapi_app.mount("/images", StaticFiles(directory=IMAGE_DIR), name="images")
fastapi_app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
fastapi_app.mount("/storage", StaticFiles(directory=OUTPUT_DIR), name="storage")

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
    conn.execute(
        "CREATE TABLE IF NOT EXISTS records ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "timestamp TEXT, "
        "plate TEXT, "
        "plate_url TEXT, "
        "car_url TEXT, "
        "status TEXT, "
        "note TEXT)"
    )
    conn.commit()
    conn.close()

init_db()

def add_record_db(plate, plate_url, car_url, status="review_needed"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        "INSERT INTO records (timestamp, plate, plate_url, car_url, status, note) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (ts, plate, plate_url, car_url, status, "")
    )
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
    res = []
    for r in rows:
        ts = r["timestamp"] if "timestamp" in r.keys() else ""
        t_str = ts.split()[1] if " " in ts else ts
        p_val = r["plate"] if "plate" in r.keys() else "UNKNOWN"
        p_img = r["plate_url"] if "plate_url" in r.keys() else ""
        c_img = r["car_url"] if "car_url" in r.keys() else ""
        st = r["status"] if "status" in r.keys() else "review_needed"
        res.append({
            "id": r["id"],
            "timestamp": ts,
            "time": t_str,
            "plate": p_val,
            "plate_number": p_val,
            "plate_url": p_img,
            "plate_image": p_img,
            "car_url": c_img,
            "car_image": c_img,
            "status": st,
            "visit_count": 1
        })
    return res

# ================= SOCKET EVENTS =================
@sio.event
async def connect(sid, environ):
    print(f"[SOCKET] Client connected: {sid}")
    global latest_payload
    if latest_payload:
        print(f">>> [SOCKET] Replaying last payload to {sid}")
        await sio.emit('notify_vehicle', latest_payload, room=sid)

@sio.event
async def disconnect(sid):
    print(f"[SOCKET] Client disconnected: {sid}")

# ================= AI LOGIC & CAMERA INITIALIZATION =================
@fastapi_app.on_event("startup")
async def startup_event():
    global main_loop, cameras, plate_sys, vehicle_sys, trigger_sys
    main_loop = asyncio.get_running_loop()
    init_db()

    video_source = os.getenv("VIDEO_SOURCE", "file").strip().lower()

    if video_source in ("rtsp", "live"):
        src1 = os.getenv("RTSP_FRONT")
        src2 = os.getenv("RTSP_BACK")
        if not src1 or not src2:
            print("\n" + "="*50)
            print("   CAMERA CONFIGURATION (RTSP MODE)")
            print("="*50)
            if not src1:
                src1 = input("INPUT: Front Camera URL/ID (default 0): ").strip() or "0"
            if not src2:
                src2 = input("INPUT: Back Camera URL/ID (default 1): ").strip() or "1"
        if isinstance(src1, str) and src1.isdigit(): src1 = int(src1)
        if isinstance(src2, str) and src2.isdigit(): src2 = int(src2)
        print(f">>> [AI] Initializing RTSP Cameras: Front={src1}, Back={src2}")
        cameras = DualCameraSystem(src1, src2, loop=False)
    else:
        src1 = os.getenv("TEST_VIDEO_FRONT", "test_videos/front.mp4")
        src2 = os.getenv("TEST_VIDEO_BACK", "test_videos/back.mp4")
        print(f">>> [AI] Initializing Test Videos (Looping): Front={src1}, Back={src2}")
        cameras = DualCameraSystem(src1, src2, loop=True)

    print(">>> [AI] Loading AI Models...")
    plate_sys = PlateRecognizer(plate_model_path=PATH_PLATE, api_key=os.getenv("GEMINI_API_KEY"))
    vehicle_sys = CarDetector(model_path=PATH_CAR)
    trigger_sys = AutoTriggerSystem(model_path=PATH_CAR, line_points=TRIGGER_LINE, cooldown=5)

    cameras.start()
    print(">>> [AI] System Ready. Starting processing loop...")
    threading.Thread(target=ai_loop, daemon=True).start()

def ai_loop():
    global current_session
    while ai_running:
        try:
            if not cameras:
                time.sleep(0.05)
                continue

            f1, f2 = cameras.get_frames()
            if f1 is None:
                time.sleep(0.02)
                continue

            if f2 is None:
                f2 = f1.copy()

            # Trigger Check on Front camera
            f_trigger = cv2.resize(f1, (640, 360))
            is_trig, tid = trigger_sys.check(f_trigger)

            # State Machine
            if current_session["state"] == "WATCHING":
                # Passive tracking to keep ByteTrack state warm and bounding boxes updated
                if vehicle_sys and f2 is not None:
                    vehicle_sys.detect(f2, capture_enabled=False)

                if is_trig:
                    print(f">>> [AI] Trigger Activated: Vehicle ID {tid}")
                    current_session.update({
                        "state": "SCANNING",
                        "start_time": time.time(),
                        "trigger_id": tid,
                        "plate_img": None,
                        "car_img": None
                    })
                    if main_loop:
                        asyncio.run_coroutine_threadsafe(
                            sio.emit('status_update', {'status': 'scanning', 'msg': f'Vehicle {tid}'}),
                            main_loop
                        )

            elif current_session["state"] == "SCANNING":
                p, _ = plate_sys.process(f1)
                if p is None and f2 is not None:
                    p, _ = plate_sys.process(f2)

                c, car_id = vehicle_sys.detect(f2)
                if c is None and f1 is not None:
                    c, car_id = vehicle_sys.detect(f1)

                if p is not None and current_session["plate_img"] is None:
                    print(f">>> [SESSION] Captured Plate")
                    current_session["plate_img"] = p

                if c is not None and current_session["car_img"] is None:
                    print(f">>> [SESSION] Captured Vehicle (ID: {car_id})")
                    current_session["car_img"] = c

                has_images = current_session["plate_img"] is not None and current_session["car_img"] is not None
                is_timeout = (time.time() - current_session["start_time"]) > 8.0

                if has_images or is_timeout:
                    reason = "SUCCESS" if has_images else "TIMEOUT"
                    p_img = current_session["plate_img"]
                    c_img = current_session["car_img"]
                    if c_img is None:
                        c_img = f2.copy() if f2 is not None else (f1.copy() if f1 is not None else None)
                        print(">>> [SESSION] Using fallback vehicle frame")
                    t_id = current_session.get("trigger_id")

                    if main_loop:
                        asyncio.run_coroutine_threadsafe(
                            finish_session_async(reason, p_img, c_img, t_id),
                            main_loop
                        )
                    current_session.update({"state": "WATCHING", "plate_img": None, "car_img": None})

            time.sleep(0.02)

        except Exception as e:
            print(f">>> [AI ERROR] {e}")
            traceback.print_exc()
            time.sleep(1)

    if cameras:
        cameras.stop()

async def finish_session_async(reason, p_img, c_img, trigger_id):
    print(f">>> [ASYNC] Finalizing Session: {reason}")
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    p_url, c_url = "/static/no_plate.jpg", "/static/no_car.jpg"

    if p_img is not None:
        fn = f"plate_{ts_str}.jpg"
        cv2.imwrite(os.path.join(IMAGE_DIR, "captures", fn), p_img)
        p_url = f"/images/captures/{fn}"

    if c_img is not None:
        fn = f"car_{ts_str}.jpg"
        cv2.imwrite(os.path.join(IMAGE_DIR, "captures", fn), c_img)
        c_url = f"/images/captures/{fn}"

    # Gemini OCR
    gemini_result = None
    if p_img is not None and os.getenv("GEMINI_API_KEY"):
        gemini_result = await plate_sys.validate_event_gemini_async(p_img, c_img)

    plate_text = "UNKNOWN"
    status = "review_needed"
    alert_mode = "VIBRATE_AND_SOUND"

    if gemini_result:
        plate_text = gemini_result.get("plate_text", "UNKNOWN")
        decision = gemini_result.get("decision", "NEED_HUMAN_CONFIRM")
        if decision == "AUTO_CONFIRM":
            status = "APPROVED"
            alert_mode = "SILENT_OK"
        if "notify" in gemini_result and "alert_mode" in gemini_result["notify"]:
            alert_mode = gemini_result["notify"]["alert_mode"]
    else:
        plate_text = f"RAW-{trigger_id}"

    new_id, str_time = add_record_db(plate_text, p_url, c_url, status=status)

    MOBILE_HOST = os.getenv("MOBILE_HOST_OVERRIDE", "").rstrip('/')
    full_p_url = f"{MOBILE_HOST}{p_url}" if MOBILE_HOST and p_url.startswith('/') else p_url
    full_c_url = f"{MOBILE_HOST}{c_url}" if MOBILE_HOST and c_url.startswith('/') else c_url

    payload = {
        "id": new_id,
        "timestamp": str_time,
        "time": str_time.split()[1] if " " in str_time else str_time,
        "plate": plate_text,
        "plate_number": plate_text,
        "image_url": full_c_url,
        "plate_image_url": full_p_url,
        "car_image": full_c_url,
        "plate_image": full_p_url,
        "car_url": full_c_url,
        "plate_url": full_p_url,
        "status": status,
        "reason": reason,
        "notify": {
            "alert_mode": alert_mode,
            "message": f"Vehicle {plate_text}"
        }
    }

    print(f">>> [SOCKET] Broadcasting: {plate_text} (#{new_id})")
    await sio.emit('notify_vehicle', payload)
    await sio.emit('review_request', payload)

    global latest_payload
    latest_payload = payload

    await sio.emit('status_update', {'status': 'watching'})

# ================= VIDEO STREAMING =================
def gen_mjpeg(cam_id):
    while True:
        if cameras:
            f1, f2 = cameras.get_frames()
            frame = f1.copy() if cam_id == 'front' and f1 is not None else (f2.copy() if f2 is not None else None)

            if frame is not None:
                orig_h, orig_w = frame.shape[:2]
                frame = cv2.resize(frame, (640, 360))
                h, w = frame.shape[:2]
                scale_x = w / orig_w
                scale_y = h / orig_h

                if vehicle_sys:
                    sz = vehicle_sys.get_safe_zone(w, h)
                    cv2.rectangle(frame, (sz[0], sz[1]), (sz[2], sz[3]), (0, 255, 0), 2)
                    cv2.putText(frame, "SAFE ZONE", (sz[0], max(15, sz[1] - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                if cam_id == 'front':
                    cv2.line(frame, TRIGGER_LINE[0], TRIGGER_LINE[1], (0, 165, 255), 2)
                    cv2.putText(frame, "TRIGGER LINE", (TRIGGER_LINE[0][0], TRIGGER_LINE[0][1] - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)

                    if trigger_sys and hasattr(trigger_sys, 'latest_tracks'):
                        for trk in trigger_sys.latest_tracks:
                            x1, y1, x2, y2 = map(int, trk['box'])
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 1)

                elif cam_id == 'back':
                    if vehicle_sys:
                        if hasattr(vehicle_sys, 'raw_detections'):
                            for (r_box, r_id) in vehicle_sys.raw_detections:
                                rcx, rcy, rw, rh = r_box
                                rcx, rcy, rw, rh = rcx * scale_x, rcy * scale_y, rw * scale_x, rh * scale_y
                                rx1, ry1 = int(rcx - rw / 2), int(rcy - rh / 2)
                                rx2, ry2 = int(rcx + rw / 2), int(rcy + rh / 2)
                                cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (0, 165, 255), 1)
                                cv2.putText(frame, f"{r_id}", (rx1, max(15, ry1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)

                        if vehicle_sys.latest_box is not None:
                            bx1, by1, bx2, by2 = vehicle_sys.latest_box
                            bx1, by1, bx2, by2 = int(bx1 * scale_x), int(by1 * scale_y), int(bx2 * scale_x), int(by2 * scale_y)
                            cv2.rectangle(frame, (bx1, by1), (bx2, by2), (0, 0, 255), 2)
                            cv2.putText(frame, f"CAPTURE: {vehicle_sys.latest_id}", (bx1, max(20, by1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                ret, buf = cv2.imencode('.jpg', frame)
                if ret:
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
        time.sleep(0.04)

# ================= REST API ROUTES =================
@fastapi_app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@fastapi_app.get("/video_feed/{cid}")
def video_feed(cid: str):
    return StreamingResponse(gen_mjpeg(cid), media_type="multipart/x-mixed-replace;boundary=frame")

@fastapi_app.get("/api/history")
def api_get_history():
    return get_recent_records(50)

@fastapi_app.post("/api/test/trigger")
async def api_test_trigger():
    """Manually trigger a vehicle detection event with live frame extraction."""
    print(">>> [TEST] Manual trigger received via /api/test/trigger")
    p_img, c_img = None, None
    tid = 999
    if cameras:
        f1, f2 = cameras.get_frames()
        if f1 is not None and plate_sys:
            p_img, _ = plate_sys.process(f1)
        if p_img is None and f2 is not None and plate_sys:
            p_img, _ = plate_sys.process(f2)

        if f2 is not None and vehicle_sys:
            c_img, cid = vehicle_sys.detect(f2)
            if cid: tid = cid
        if c_img is None and f1 is not None and vehicle_sys:
            c_img, cid = vehicle_sys.detect(f1)
            if cid: tid = cid

        if c_img is None:
            c_img = f2.copy() if f2 is not None else (f1.copy() if f1 is not None else None)

    await finish_session_async("Manual Test Trigger", p_img, c_img, tid)
    return {"status": "success", "message": f"Simulated vehicle event triggered (ID: {tid})"}

# --- STAFF CONFIRMATION ENDPOINTS (CV Feature: Flags uncertain reads for staff confirmation) ---
@fastapi_app.post("/api/ingest/confirm")
async def api_ingest_confirm(
    plate: str = Form(...),
    timestamp: str = Form(...),
    image: UploadFile = File(None),
    plate_image: UploadFile = File(None)
):
    try:
        print(f">>> [STAFF CONFIRM] Received confirmation: {plate} at {timestamp}")
        safe_plate = "".join([c for c in plate if c.isalnum() or c in ('-', '_')])
        base_dir = OUTPUT_DIR

        # Find next sequential counter
        count = 1
        while True:
            candidate = os.path.join(base_dir, f"{safe_plate}_{count}")
            if not os.path.exists(candidate):
                save_dir = candidate
                break
            count += 1
        os.makedirs(save_dir, exist_ok=True)

        async def save_upload(upload_file, suffix):
            if not upload_file: return None
            content = await upload_file.read()
            nparr = np.frombuffer(content, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None: return None
            img = cv2.resize(img, (640, 480))
            cv2.putText(img, timestamp, (20, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            fname = f"{safe_plate}_{suffix}.jpg"
            cv2.imwrite(os.path.join(save_dir, fname), img)
            return fname

        car_fname = await save_upload(image, "car")
        plate_fname = await save_upload(plate_image, "plate")

        info = {
            "plate": plate,
            "count": count,
            "folder_name": os.path.basename(save_dir),
            "timestamp": timestamp,
            "car_image": car_fname,
            "plate_image": plate_fname,
            "confirmed_by": "staff"
        }
        with open(os.path.join(save_dir, "info.json"), "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        # Update status in database
        conn = sqlite3.connect(DB_NAME)
        conn.execute("UPDATE records SET status = 'APPROVED' WHERE plate = ?", (plate,))
        conn.commit()
        conn.close()

        # Emit update to all connected web & mobile clients
        await sio.emit('status_update', {'status': 'confirmed', 'plate': plate})

        return {"status": "success", "message": f"Saved to {save_dir}"}

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@fastapi_app.get("/api/ingest/history")
async def api_ingest_history():
    if not os.path.exists(OUTPUT_DIR):
        return []
    history = []
    for entry in os.scandir(OUTPUT_DIR):
        if entry.is_dir():
            info_file = os.path.join(entry.path, "info.json")
            if os.path.exists(info_file):
                try:
                    with open(info_file, "r", encoding="utf-8") as f:
                        history.append(json.load(f))
                except Exception:
                    pass
    history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    return history

# ================= ENTRY POINT =================
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def main():
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "8001"))
    ip = get_local_ip()
    v_src = os.getenv("VIDEO_SOURCE", "file")

    print("="*60)
    print("   DKAI VEHICLE MONITORING & RECOGNITION SERVER")
    print(f"   Mode:         {v_src.upper()}")
    print(f"   Database:     {DB_NAME}")
    print(f"   Local Access: http://localhost:{port}")
    print(f"   LAN Access:   http://{ip}:{port}")
    print("="*60)

    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()
