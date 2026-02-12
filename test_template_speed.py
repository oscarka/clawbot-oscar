import cv2
import time
import os

def test_speed():
    # 1. Load the existing screenshot
    screenshot_path = "debug_screenshot.png"
    if not os.path.exists(screenshot_path):
        print("❌ debug_screenshot.png not found. Please run the agent once to generate it.")
        return

    img = cv2.imread(screenshot_path)
    if img is None:
        print("❌ Failed to load image.")
        return
        
    print(f"🖼️  Image Size: {img.shape[1]}x{img.shape[0]}")

    # 2. Simulate a template (Crop a 64x64 chunk from the center)
    # In reality, this would be the 'Send' icon loaded from a file
    h, w, _ = img.shape
    cx, cy = w // 2, h // 2
    template = img[cy:cy+64, cx:cx+64]
    
    cv2.imwrite("temp_template_sample.png", template)
    print("📋 Generated sample template (64x64) from center.")

    # 3. Run Benchmark
    print("⏱️  Running Template Matching Benchmark (100 iterations)...")
    
    start_time = time.time()
    iterations = 100
    
    for _ in range(iterations):
        result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
    end_time = time.time()
    
    total_time = end_time - start_time
    avg_time = (total_time / iterations) * 1000 # to ms
    
    print(f"\n🚀 Performance Result (Original 2880x1800):")
    print(f"   Total Time (100 runs): {total_time:.4f}s")
    print(f"   Avg Time per match:    {avg_time:.2f} ms")

    # --- Optimization: Downscale 50% ---
    print("\n⚡️ Optimization: Testing with 50% Downscale (1440x900)...")
    img_small = cv2.resize(img, (0, 0), fx=0.5, fy=0.5)
    template_small = cv2.resize(template, (0, 0), fx=0.5, fy=0.5)
    
    start_time = time.time()
    for _ in range(iterations):
        result = cv2.matchTemplate(img_small, template_small, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    end_time = time.time()
    
    avg_time_opt = ((end_time - start_time) / iterations) * 1000
    print(f"   Avg Time (Optimized):  {avg_time_opt:.2f} ms")
    
    if avg_time_opt < 100:
        print("\n✅ Conclusion: OPTIMIZED SPEED IS ACCEPTABLE (<100ms).")
    else:
        print("\n⚠️ Conclusion: STILL SLOW.")

if __name__ == "__main__":
    test_speed()
