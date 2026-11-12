import unittest

class TestSmokeImports(unittest.TestCase):
    def test_import_vehicle_detector(self):
        import src.vehicle_detector as vd
        self.assertTrue(hasattr(vd, "CarDetector"))

    def test_import_plate_detector(self):
        import src.plate_detector as pd
        self.assertTrue(hasattr(pd, "PlateRecognizer"))

    def test_import_auto_trigger(self):
        import src.auto_trigger as at
        self.assertTrue(hasattr(at, "AutoTriggerSystem"))

    def test_import_camera_manager(self):
        import src.camera_manager as cm
        self.assertTrue(hasattr(cm, "CameraStream"))
        self.assertTrue(hasattr(cm, "DualCameraSystem"))

    def test_import_database(self):
        import src.database as db
        self.assertTrue(hasattr(db, "init_db"))
        self.assertTrue(hasattr(db, "add_record"))

if __name__ == "__main__":
    unittest.main()
