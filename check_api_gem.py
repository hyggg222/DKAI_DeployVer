import google.generativeai as genai
import os
import time

# 1. Điền API Key của bạn
os.environ["GOOGLE_API_KEY"] = "AIzaSyAgN5gHb1pFEqH9pXzOcP-whZMLDSGWVh0"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

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