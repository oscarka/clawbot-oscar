import cv2
import os

def crop_send_icon():
    screenshot_path = "debug_screenshot.png"
    if not os.path.exists(screenshot_path):
        print("❌ Screenshot not found")
        return

    img = cv2.imread(screenshot_path)
    # Coordinates estimated from previous logs where Send button was (approx)
    # The user's screenshot was 2880x1800.
    # Previous successful click was around (1324, 828) which is roughly bottom right quadrant.
    # Let's crop a generous region around the bottom right corner first to help locate it visually,
    # or just crop a fixed coordinate if we are sure.
    # From the logs, the brute force click was at (1324, 828).
    # Let's crop a 60x60 box around that.
    
    x, y = 1324, 828
    h, w = 60, 60
    
    # Adjust for crop boundary
    top = max(0, y - h//2)
    bottom = min(img.shape[0], y + h//2)
    left = max(0, x - w//2)
    right = min(img.shape[1], x + w//2)
    
    crop = img[top:bottom, left:right]
    
    output_path = "icon_send.png"
    cv2.imwrite(output_path, crop)
    print(f"✅ Cropped Send icon to {output_path}")

if __name__ == "__main__":
    crop_send_icon()
