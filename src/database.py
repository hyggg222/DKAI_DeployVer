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
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
    
    if not plate_num: plate_num = "UNKNOWN"
    
    c.execute("INSERT INTO records (timestamp, plate_number, plate_image, car_image, status, note) VALUES (?, ?, ?, ?, ?, ?)",
              (timestamp, plate_num, plate_img, car_img, 'review_needed', ''))
    
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    return new_id, timestamp
def count_plate_visits(plate_number):
    if not plate_number or "UNKNOWN" in plate_number or "Scan" in plate_number:
        return 0
        
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
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

def get_all_archived_records():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row 
    c = conn.cursor()
    c.execute("SELECT * FROM records WHERE status != 'deleted' ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(ix) for ix in rows]

def get_today_records():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row 
    c = conn.cursor()
    c.execute("SELECT * FROM records WHERE status = 'review_needed' OR status = 'approved' ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    return [dict(ix) for ix in rows]

def clear_all_records():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM records") 
    c.execute("DELETE FROM sqlite_sequence WHERE name='records'")
    conn.commit()
    conn.close()
    print(">>> [DB] Delete all data.")

def get_record_by_id(record_id):
    """Lấy thông tin bản ghi theo ID"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM records WHERE id = ?", (record_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None
