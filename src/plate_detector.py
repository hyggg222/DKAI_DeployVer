import cv2
import numpy as np
try:
    from ultralytics import YOLO
except Exception:
    YOLO = None
import base64
import json
import requests
import re
import time

class PlateRecognizer:
    def __init__(self, plate_model_path, api_key=None):
        if YOLO is None:
            raise RuntimeError("YOLO could not be imported. Please ensure ultralytics and PyTorch are installed.")
        print(f"Loading Plate Detector (Continuous Hunting Mode): {plate_model_path}")
        self.plate_model = YOLO(plate_model_path)
        self.api_key = api_key
        
        self.best_candidate = {
            "img": None,
            "conf": 0.0,
            "timestamp": 0
        }

    def process(self, frame, expansion_percentage=0.15):
        if self.best_candidate['img'] is not None:
            if time.time() - self.best_candidate['timestamp'] > 15.0:
                self.best_candidate = {"img": None, "conf": 0.0, "timestamp": 0}

        results = self.plate_model(frame, verbose=False, conf=0.4)
        
        current_best_crop = None
        current_best_conf = 0.0

        if len(results) > 0 and len(results[0].boxes) > 0:
            best_box = max(results[0].boxes, key=lambda x: x.conf[0])
            conf = float(best_box.conf[0])
            
            x1, y1, x2, y2 = map(int, best_box.xyxy[0])
            
            box_w = x2 - x1
            box_h = y2 - y1
            
            if box_w > 40 and box_h > 10:
                h_img, w_img = frame.shape[:2]

                pad_x = int(box_w * expansion_percentage) 
                pad_y = int(box_h * expansion_percentage)

                new_x1 = max(0, x1 - pad_x)
                new_y1 = max(0, y1 - pad_y)
                new_x2 = min(w_img, x2 + pad_x)
                new_y2 = min(h_img, y2 + pad_y)
                
                current_best_crop = frame[new_y1:new_y2, new_x1:new_x2].copy()
                current_best_conf = conf

        if current_best_crop is not None:
            if current_best_conf > self.best_candidate['conf']:
                self.best_candidate['img'] = current_best_crop
                self.best_candidate['conf'] = current_best_conf
                self.best_candidate['timestamp'] = time.time()
                return current_best_crop, current_best_conf 

        return None, 0.0

    def get_and_clear_best_result(self):
        img = self.best_candidate['img']
        conf = self.best_candidate['conf']
        
        self.best_candidate = {"img": None, "conf": 0.0, "timestamp": 0}
        
        return img, conf

    def recognize_gemini(self, img_crop):
        if img_crop is None:
            print(">>> [GEMINI] Error: Image null")
            return None
            
        if not self.api_key or "YOUR_KEY" in self.api_key:
            print(">>> [GEMINI] Error: Missing or failed API")
            return None

        h, w = img_crop.shape[:2]
        if w > 1024:
            scale = 1024 / w
            img_crop = cv2.resize(img_crop, (1024, int(h*scale)))

        success, buffer = cv2.imencode('.jpg', img_crop)
        if not success: return None
        b64_img = base64.b64encode(buffer).decode("utf-8")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={self.api_key}"
        
        prompt = """
        Analyze this license plate image.
        1. Read the text strictly (letters and numbers only).
        2. Detect the background color (white, yellow, or blue).
        3. Return ONLY a JSON object like this: {"text": "30A12345", "color": "white"}
        NO MARKDOWN, NO EXPLANATION.
        """
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt}, 
                    {"inline_data": {"mime_type": "image/jpeg", "data": b64_img}}
                ]
            }],
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ],
            "generationConfig": {
                "response_mime_type": "application/json"
            }
        }

        try:
            resp = requests.post(url, json=payload, timeout=10)
            
            if resp.status_code != 200:
                print(f">>> [GEMINI] HTTP Error {resp.status_code}: {resp.text}")
                return None

            resp_json = resp.json()
            
            if "promptFeedback" in resp_json and "blockReason" in resp_json["promptFeedback"]:
                print(f">>> [GEMINI] Block: {resp_json['promptFeedback']['blockReason']}")
                return None
            
            if "candidates" not in resp_json or not resp_json["candidates"]:
                print(">>> [GEMINI] Return null (Cannot read)")
                return None

            raw_text = resp_json['candidates'][0]['content']['parts'][0]['text']
            
            data = json.loads(raw_text)
            text = re.sub(r'[^a-zA-Z0-9]', '', data.get('text', ''))
            color = data.get('color', 'white').lower()
            
            c_code = 't'
            if 'yellow' in color: c_code = 'v'
            elif 'blue' in color: c_code = 'x'
            
            final_res = f"bs{text.lower()}{c_code}"
            print(f">>> [GEMINI] Success: {final_res}")
            return final_res

        except Exception as e:
            print(f">>> [GEMINI] Exception Error: {e}")
        
        return None
