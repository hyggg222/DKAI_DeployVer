import google.generativeai as genai
import os
import time

from dotenv import load_dotenv

load_dotenv()

# 1. Điền API Key của bạn (đã được load từ file .env)
api_key = os.getenv("GEMINI_API_KEY") 
if not api_key:
    # Fallback for manual testing if env not set
    # api_key = "YOUR_KEY_HERE" 
    print("Warning: GEMINI_API_KEY not found in environment variables.")

genai.configure(api_key=api_key)

# 2. Chọn model cần test (Bản Experimental)
model_name = "gemini-2.0-flash-exp" 
print(f"📡 Đang kết nối tới: {model_name} ...")

try:
    model = genai.GenerativeModel(model_name)
    
    # 3. Gửi 1 request đơn giản
    start = time.time()
    response = model.generate_content("Chào Gemini, hãy xác nhận bạn đang hoạt động.")
    end = time.time()
    
    print("-" * 30)
    print(f"✅ KẾT QUẢ: THÀNH CÔNG!")
    print(f"⏱️ Thời gian phản hồi: {end - start:.2f} giây")
    print(f"🤖 Phản hồi: {response.text}")
    print("-" * 30)
    print("👉 Kết luận: Model này KHÔNG bị limit 0. Dùng được cho DKAI!")

except Exception as e:
    print("-" * 30)
    print(f"❌ KẾT QUẢ: THẤT BẠI")
    print(f"Lỗi chi tiết: {e}")
    print("-" * 30)