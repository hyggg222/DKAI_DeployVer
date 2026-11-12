import unittest
import numpy as np
from src.vehicle_detector import CarDetector

class DummyCarDetector(CarDetector):
    def __init__(self):
        # Override to avoid loading weights during unit logic testing
        self.margin = 0.02
        self.zone_x_min = self.margin
        self.zone_x_max = 1 - self.margin
        self.zone_y_min = self.margin
        self.zone_y_max = 1 - self.margin
        self.min_area_ratio = 0.03
        self.max_occlusion_ratio = 0.05
        self.latest_box = None
        self.latest_id = None

class TestVehicleDetectorLogic(unittest.TestCase):
    def setUp(self):
        self.detector = DummyCarDetector()

    def test_safe_zone_calculation(self):
        w, h = 1000, 500
        x1, y1, x2, y2 = self.detector.get_safe_zone(w, h)
        self.assertEqual(x1, 20)
        self.assertEqual(y1, 10)
        self.assertEqual(x2, 980)
        self.assertEqual(y2, 490)

    def test_is_cut_off(self):
        frame_w, frame_h = 640, 480
        
        # Center box: cx=320, cy=240, w=100, h=100 -> not cut off
        self.assertFalse(self.detector.is_cut_off([320, 240, 100, 100], frame_w, frame_h))
        
        # Box touching left edge: x1 = 10 - 20 = -10 < 15 -> cut off
        self.assertTrue(self.detector.is_cut_off([10, 240, 40, 40], frame_w, frame_h))
        
        # Box touching right edge: x2 = 630 + 20 = 650 > 640 - 15 -> cut off
        self.assertTrue(self.detector.is_cut_off([630, 240, 40, 40], frame_w, frame_h))

    def test_is_full_box_in_zone(self):
        video_w, video_h = 1000, 1000
        # Fully inside
        self.assertTrue(self.detector.is_full_box_in_zone([500, 500, 200, 200], video_w, video_h))
        # Crossing margin boundary
        self.assertFalse(self.detector.is_full_box_in_zone([10, 500, 100, 100], video_w, video_h))

    def test_smart_crop_75(self):
        frame = np.zeros((400, 400, 3), dtype=np.uint8)
        xywh = [200, 200, 100, 100]
        crop = self.detector.smart_crop_75(frame, xywh)
        self.assertIsNotNone(crop)
        self.assertGreater(crop.shape[0], 0)
        self.assertGreater(crop.shape[1], 0)

    def test_calculate_occlusion(self):
        candidate = [100, 100, 50, 50]
        other_overlapping = [[100, 100, 50, 50]]
        other_distant = [[300, 300, 50, 50]]
        
        # Full overlap
        occ_high = self.detector.calculate_occlusion(candidate, other_overlapping)
        self.assertAlmostEqual(occ_high, 1.0, places=2)
        
        # No overlap
        occ_zero = self.detector.calculate_occlusion(candidate, other_distant)
        self.assertEqual(occ_zero, 0.0)

if __name__ == "__main__":
    unittest.main()
