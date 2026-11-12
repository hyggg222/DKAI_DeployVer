import os
import unittest
import tempfile
import src.database as db

class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_registry.db")
        self.orig_db_name = db.DB_NAME
        db.DB_NAME = self.db_path
        db.init_db()

    def tearDown(self):
        db.DB_NAME = self.orig_db_name
        self.temp_dir.cleanup()

    def test_init_db_creates_table(self):
        self.assertTrue(os.path.exists(self.db_path))

    def test_add_and_get_record(self):
        rec_id, ts = db.add_record("30A12345", "plate.jpg", "car.jpg")
        self.assertIsNotNone(rec_id)
        
        row = db.get_record_by_id(rec_id)
        self.assertIsNotNone(row)
        self.assertEqual(row["plate_number"], "30A12345")
        self.assertEqual(row["plate_image"], "plate.jpg")
        self.assertEqual(row["car_image"], "car.jpg")
        self.assertEqual(row["status"], "review_needed")

    def test_update_status(self):
        rec_id, _ = db.add_record("51F99999", "p.jpg", "c.jpg")
        db.update_status(rec_id, "approved")
        
        row = db.get_record_by_id(rec_id)
        self.assertEqual(row["status"], "approved")

    def test_update_plate_number(self):
        rec_id, _ = db.add_record("UNKNOWN", "p.jpg", "c.jpg")
        db.update_plate_number(rec_id, "29A88888")
        
        row = db.get_record_by_id(rec_id)
        self.assertEqual(row["plate_number"], "29A88888")

    def test_count_plate_visits(self):
        db.add_record("30A12345", "p1.jpg", "c1.jpg")
        db.add_record("30A12345", "p2.jpg", "c2.jpg")
        count = db.count_plate_visits("30A12345")
        self.assertEqual(count, 2)

    def test_get_today_records(self):
        db.add_record("30A11111", "p.jpg", "c.jpg")
        records = db.get_today_records()
        self.assertGreaterEqual(len(records), 1)

    def test_clear_all_records(self):
        db.add_record("30A11111", "p.jpg", "c.jpg")
        db.clear_all_records()
        records = db.get_all_archived_records()
        self.assertEqual(len(records), 0)

if __name__ == "__main__":
    unittest.main()
