
import cv2
import numpy as np
import os

IMAGE_DIR = "images_test"
os.makedirs(IMAGE_DIR, exist_ok=True)

# Create a gray image
img = np.zeros((300, 300, 3), dtype=np.uint8)
img[:] = (200, 200, 200)

# Add Text
cv2.putText(img, "NO IMAGE", (70, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (50, 50, 50), 2)

# Save
cv2.imwrite(os.path.join(IMAGE_DIR, "no_car.jpg"), img)
cv2.imwrite(os.path.join(IMAGE_DIR, "no_plate.jpg"), img)

print("Placeholder images created in images_test/")
