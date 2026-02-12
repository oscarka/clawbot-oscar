
import Quartz
from AppKit import NSScreen
from PIL import Image
import subprocess
import os

def get_screen_info():
    main_display_id = Quartz.CGMainDisplayID()
    width = Quartz.CGDisplayPixelsWide(main_display_id)
    height = Quartz.CGDisplayPixelsHigh(main_display_id)
    
    # Get backing scale factor (Retina 2.0 vs 1.0)
    screen = NSScreen.mainScreen()
    scale = screen.backingScaleFactor() if screen else 1.0
    
    print(f"🖥️  Logical Screen Size: {width}x{height}")
    print(f"🔍 Retina Scale Factor: {scale}")
    
    return width, height, scale

def capture_and_check():
    filename = "debug_screenshot.png"
    subprocess.run(["screencapture", "-x", filename])
    
    if os.path.exists(filename):
        img = Image.open(filename)
        print(f"📸 Screenshot Resolution: {img.width}x{img.height}")
        
        screen_w, screen_h, scale = get_screen_info()
        
        expected_w = int(screen_w * scale)
        expected_h = int(screen_h * scale)
        
        if img.width == expected_w and img.height == expected_h:
            print("✅ Resolution Matches (Logical * Scale = Screenshot)")
        else:
            print(f"⚠️ Resolution Mismatch!")
            print(f"   Expected: {expected_w}x{expected_h}")
            print(f"   Actual:   {img.width}x{img.height}")

if __name__ == "__main__":
    capture_and_check()
