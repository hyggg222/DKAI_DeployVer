import sqlite3
from datetime import datetime
import os

DB_NAME = "registry.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
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

def add_record(plate_num, plate_img, car_img):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # Lưu đầy đủ ngày giờ
    
    if not plate_num: plate_num = "UNKNOWN"
    
    c.execute("INSERT INTO records (timestamp, plate_number, plate_image, car_image, status, note) VALUES (?, ?, ?, ?, ?, ?)",
              (timestamp, plate_num, plate_img, car_img, 'review_needed', ''))
    
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id, timestamp

# --- HÀM MỚI: Đếm số lần xe đã vào (dựa theo biển số) ---
def count_plate_visits(plate_number):
    """Đếm xem biển số này đã xuất hiện bao nhiêu lần (chỉ tính các lần đã Approved)"""
    if not plate_number or "UNKNOWN" in plate_number or "Scan" in plate_number:
        return 0
        
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Đếm số dòng có cùng biển số
    c.execute("SELECT COUNT(*) FROM records WHERE plate_number = ? AND status != 'deleted'", (plate_number,))
    count = c.fetchone()[0]
    conn.close()
    return count

def update_status(record_id, status):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE records SET status = ? WHERE id = ?", (status, record_id))
    conn.commit()
    conn.close()

def update_plate_number(record_id, new_plate):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE records SET plate_number = ? WHERE id = ?", (new_plate, record_id))
    conn.commit()
    conn.close()

# --- HÀM MỚI: Lấy toàn bộ hồ sơ cho trang Archive ---
def get_all_archived_records():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row 
    c = conn.cursor()
    # Lấy tất cả, sắp xếp mới nhất lên đầu
    c.execute("SELECT * FROM records WHERE status != 'deleted' ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(ix) for ix in rows]

def get_today_records():
    """Chỉ lấy 20 xe gần nhất cho trang Live"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row 
    c = conn.cursor()
    c.execute("SELECT * FROM records WHERE status = 'review_needed' OR status = 'approved' ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    return [dict(ix) for ix in rows]

def clear_all_records():
    """Xóa toàn bộ dữ liệu trong bảng records"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM records") # Xóa hết dữ liệu
    c.execute("DELETE FROM sqlite_sequence WHERE name='records'") # Reset bộ đếm ID về 1
    conn.commit()
    conn.close()
    print(">>> [DB] Đã xóa sạch dữ liệu database.")

def get_record_by_id(record_id):
    """Lấy thông tin bản ghi theo ID"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM records WHERE id = ?", (record_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None
