import time
import Quartz
import Vision
# import CoreImage  <-- Removed to avoid dependency issue
from Cocoa import NSURL
import sys

def benchmark_ocr():
    print("🚀 开始基准测试: macOS Native Vision OCR...")
    
    # 1. 屏幕捕获 (CGImage)
    measure_start = time.time()
    img_ref = Quartz.CGWindowListCreateImage(
        Quartz.CGRectInfinite,
        Quartz.kCGWindowListOptionOnScreenOnly,
        0,
        Quartz.kCGWindowImageDefault
    )
    
    capture_time = time.time() - measure_start
    print(f"📸 屏幕捕获耗时: {capture_time*1000:.2f} ms")
    
    if not img_ref:
        print("❌ 屏幕捕获失败")
        return

    # 2. 图像处理 (直接使用 CGImage，无需 CoreImage)
    convert_start = time.time()
    # 使用 initWithCGImage:options: 代替 initWithCIImage:options:
    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img_ref, None)
    convert_time = time.time() - convert_start
    # print(f"🖼️  图像准备耗时: {convert_time*1000:.2f} ms")

    # 3. OCR 识别
    ocr_start = time.time()
    
    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelFast)
    request.setUsesLanguageCorrection_(False)
    
    success, error = handler.performRequests_error_([request], None)
    
    if not success:
        print(f"❌ OCR 请求失败: {error}")
        return

    results = request.results()
    text_count = len(results)
    
    ocr_time = time.time() - ocr_start
    print(f"⚡️ OCR 识别耗时: {ocr_time*1000:.2f} ms")
    
    total_time = capture_time + convert_time + ocr_time
    print(f"⏱️  总流程耗时:   {total_time*1000:.2f} ms")
    print(f"📊 识别到的文本行数: {text_count}")
    
    if text_count > 0:
        # get string from first observation
        first_text = results[0].topCandidates_(1)[0].string()
        print(f"📝 示例文本: {first_text}")

    # 4. 再次运行 (预热)
    print("\n🔄 运行第2次 (预热后)...")
    start_2 = time.time()
    img_ref_2 = Quartz.CGWindowListCreateImage(
        Quartz.CGRectInfinite,
        Quartz.kCGWindowListOptionOnScreenOnly,
        0,
        Quartz.kCGWindowImageDefault
    )
    # create handler with CGImage again
    handler_2 = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img_ref_2, None)
    handler_2.performRequests_error_([request], None)
    end_2 = time.time()
    print(f"⚡️ 第2次总耗时: {(end_2 - start_2)*1000:.2f} ms")

if __name__ == "__main__":
    try:
        benchmark_ocr()
    except ImportError as e:
        print(f"❌ 缺少库: {e}")
    except Exception as e:
        print(f"❌ 测试出错: {e}")
