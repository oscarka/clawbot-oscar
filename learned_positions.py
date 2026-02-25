#!/usr/bin/env python3
"""
人机配合学习：记住用户辅助点击的位置，供下次直接使用
支持：绝对坐标、相对位置、视觉模板、AX 路径、描述（供 vision/YOLO）
"""

import json
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

# 缓存与模板目录
CACHE_DIR = Path.home() / ".moltbot"
TEMPLATES_DIR = CACHE_DIR / "templates"
CACHE_FILE = CACHE_DIR / "learned_positions.json"


def _ensure_dirs():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


def _load_cache() -> dict:
    _ensure_dirs()
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(data: dict):
    _ensure_dirs()
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _cache_key(app: str, action: str) -> str:
    return f"{app}::{action}"


def _safe_filename(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in s)


def _normalize_app(app: str) -> str:
    """飞书/Lark 统一为飞书，保证缓存 key 一致"""
    if app in ("Lark", "飞书"):
        return "飞书"
    return app


def _to_click_coords(x: float, y: float, screenshot_path: str = None) -> Tuple[int, int]:
    """
    Vision 返回的坐标是截图像素，Retina 下需转为点击坐标（points）
    NSScreen.frame 是 points，截图是 pixels
    """
    try:
        from AppKit import NSScreen
        screen = NSScreen.mainScreen()
        if not screen:
            return (int(x), int(y))
        screen_w_pts = screen.frame().size.width
        if not screenshot_path:
            tmp = str(CACHE_DIR / "_scale_check.png")
            r = subprocess.run(["peekaboo", "image", "--mode", "screen", "--path", tmp], capture_output=True, timeout=5)
            screenshot_path = tmp if r.returncode == 0 and Path(tmp).exists() else None
        if screenshot_path and Path(screenshot_path).exists():
            import cv2
            img = cv2.imread(screenshot_path)
            if img is not None and screen_w_pts > 0:
                img_w = img.shape[1]
                scale = img_w / screen_w_pts
                if scale > 1.1:
                    result = (int(x / scale), int(y / scale))
                    if "_scale_check" in str(screenshot_path):
                        Path(screenshot_path).unlink(missing_ok=True)
                    return result
    except Exception:
        pass
    return (int(x), int(y))


# --- 精简版（仅坐标，兼容旧版）---
def get_learned_position(app: str, action: str) -> Optional[Tuple[int, int]]:
    """获取已学习的点击位置（纯坐标，兼容旧逻辑）"""
    entry = _get_full_entry(app, action)
    if not entry or "x" not in entry or "y" not in entry:
        return None
    return (int(entry["x"]), int(entry["y"]))


def save_learned_position(app: str, action: str, x: int, y: int):
    """保存用户辅助确认的点击位置（仅坐标，兼容旧逻辑）"""
    cache = _load_cache()
    key = _cache_key(app, action)
    cache[key] = {
        "app": app,
        "action": action,
        "x": x,
        "y": y,
    }
    _save_cache(cache)


def _get_full_entry(app: str, action: str) -> Optional[Dict]:
    """获取完整学习条目"""
    app = _normalize_app(app)
    cache = _load_cache()
    return cache.get(_cache_key(app, action))


# --- 丰富学习：视觉模板、AX 路径、相对位置 ---

def capture_rich_at_position(
    app: str,
    action: str,
    x: int,
    y: int,
    description: str = "",
) -> Dict[str, Any]:
    """
    在人机配合确认的位置处，采集丰富信息：
    - 绝对坐标 (x, y)
    - 视觉模板：截取目标区域并裁剪保存
    - 相对位置：相对屏幕/窗口的比例（应用缩放后仍可用）
    - AX 路径：该坐标下的 AX 元素路径（供 AX 查找）
    - 描述：供 vision 模型使用的文字描述
    """
    import time
    from datetime import datetime

    entry = {
        "app": app,
        "action": action,
        "x": x,
        "y": y,
        "learned_at": datetime.now().isoformat(),
        "description": description or f"{action}",
    }

    # 1. 视觉模板：截屏并裁剪目标区域
    try:
        import cv2
        screenshot_path = str(CACHE_DIR / f"capture_{int(time.time())}.png")
        result = subprocess.run(
            ["peekaboo", "image", "--mode", "screen", "--path", screenshot_path],
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0 and Path(screenshot_path).exists():
            img = cv2.imread(screenshot_path)
            if img is not None:
                h_img, w_img = img.shape[:2]
                crop_size = 80
                x1 = max(0, x - crop_size // 2)
                y1 = max(0, y - crop_size // 2)
                x2 = min(w_img, x1 + crop_size)
                y2 = min(h_img, y1 + crop_size)
                crop = img[y1:y2, x1:x2]
                template_path = TEMPLATES_DIR / f"{_safe_filename(app)}_{_safe_filename(action)}.png"
                cv2.imwrite(str(template_path), crop)
                entry["visual"] = {
                    "template_path": str(template_path),
                    "crop_center": [x, y],
                    "crop_size": crop_size,
                }
            Path(screenshot_path).unlink(missing_ok=True)
    except Exception:
        pass

    # 2. 相对位置：相对屏幕 + 相对窗口（窗口缩放/移动后仍可用）
    try:
        from AppKit import NSScreen
        screen = NSScreen.mainScreen()
        sw, sh = 0, 0
        if screen:
            f = screen.frame()
            sw, sh = f.size.width, f.size.height
            rel_x = x / sw if sw else 0
            rel_y = (sh - y) / sh if sh else 0
            entry["relative"] = {
                "screen_w": sw,
                "screen_h": sh,
                "rel_x": rel_x,
                "rel_y": rel_y,
            }
        # 窗口相对：更抗窗口缩放/移动
        from ax_poc import capture_ax_tree
        result = capture_ax_tree(app)
        if not result:
            result = capture_ax_tree("Lark" if "飞书" in app else "飞书")
        if result and sh > 0:
            _, root = result
            if root.frame:
                wx, wy, ww, wh = root.frame
                wy_top = sh - wy - wh
                rel_in_window_x = (x - wx) / ww if ww else 0
                rel_in_window_y = (y - wy_top) / wh if wh else 0
                entry["window_relative"] = {
                    "rel_x": rel_in_window_x,
                    "rel_y": rel_in_window_y,
                    "window_w": ww,
                    "window_h": wh,
                }
    except Exception:
        pass

    # 3. AX 路径：尝试从 ax_poc 获取该坐标下的元素路径
    try:
        from ax_poc import capture_ax_tree, find_element_at_point
        result = capture_ax_tree(app)
        if not result:
            result = capture_ax_tree("Lark" if "飞书" in app else "飞书")
        if result:
            _, root = result
            path = find_element_at_point(root, x, y)
            if path:
                entry["ax_path"] = path
    except Exception:
        pass

    return entry


def save_learned_rich(app: str, action: str, x: int, y: int, description: str = "", from_vision: bool = False):
    """采集并保存丰富学习信息。from_vision=True 时：模板用原坐标裁剪，保存用 Retina 转换后的坐标"""
    app = _normalize_app(app)
    x_click, y_click = _to_click_coords(x, y) if from_vision else (x, y)
    entry = capture_rich_at_position(app, action, x, y, description)  # 模板用原坐标
    entry["x"], entry["y"] = x_click, y_click  # 保存点击坐标系
    cache = _load_cache()
    cache[_cache_key(app, action)] = entry
    _save_cache(cache)
    print(f"   💾 已保存到 {CACHE_FILE}")


def find_using_learned(
    app: str,
    action: str,
    screenshot_path: str = None,
) -> Optional[Tuple[int, int]]:
    """
    使用已学习信息查找目标坐标
    策略顺序：1.绝对坐标（最可靠） 2.窗口相对 3.屏幕相对 4.模板匹配 5.AX路径
    返回: (x, y) 或 None
    """
    app = _normalize_app(app)
    entry = _get_full_entry(app, action)
    if not entry:
        return None

    # 1. 绝对坐标：同窗口位置时最可靠
    if "x" in entry and "y" in entry:
        return (int(entry["x"]), int(entry["y"]))

    # 2. 窗口相对
    wr = entry.get("window_relative")
    if wr:
        try:
            from ax_poc import capture_ax_tree
            from AppKit import NSScreen
            result = capture_ax_tree(app)
            if not result:
                result = capture_ax_tree("Lark" if "飞书" in app else "飞书")
            if result:
                _, root = result
                if root.frame:
                    screen = NSScreen.mainScreen()
                    sh = screen.frame().size.height if screen else 0
                    wx, wy, ww, wh = root.frame
                    wy_top = sh - wy - wh
                    rx, ry = wr.get("rel_x"), wr.get("rel_y")
                    if rx is not None and ry is not None and ww and wh:
                        x = int(wx + rx * ww)
                        y = int(wy_top + ry * wh)
                        return (x, y)
        except Exception:
            pass

    # 3. 屏幕相对
    rel = entry.get("relative")
    if rel:
        try:
            from AppKit import NSScreen
            screen = NSScreen.mainScreen()
            if screen:
                f = screen.frame()
                sw, sh = f.size.width, f.size.height
                rx, ry = rel.get("rel_x"), rel.get("rel_y")
                if rx is not None and ry is not None:
                    x = int(rx * sw)
                    y = int(sh - ry * sh)  # 转回左上
                    return (x, y)
        except Exception:
            pass

    # 4. 模板匹配
    visual = entry.get("visual", {})
    template_path = visual.get("template_path")
    if template_path and Path(template_path).exists():
        try:
            import cv2
            if not screenshot_path:
                tmp = str(CACHE_DIR / "find_screenshot.png")
                subprocess.run(["peekaboo", "image", "--mode", "screen", "--path", tmp], capture_output=True, timeout=10)
                screenshot_path = tmp
            if Path(screenshot_path).exists():
                img = cv2.imread(screenshot_path)
                template = cv2.imread(template_path)
                if img is not None and template is not None:
                    # 多尺度尝试（窗口可能缩放）
                    for scale in [1.0, 1.25, 0.8]:
                        if scale != 1.0:
                            tw, th = template.shape[1], template.shape[0]
                            template_s = cv2.resize(template, (int(tw * scale), int(th * scale)))
                        else:
                            template_s = template
                        result = cv2.matchTemplate(img, template_s, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, max_loc = cv2.minMaxLoc(result)
                        if max_val >= 0.7:
                            w, h = template_s.shape[1], template_s.shape[0]
                            cx = max_loc[0] + w // 2
                            cy = max_loc[1] + h // 2
                            return (cx, cy)
        except Exception:
            pass

    # 5. AX 路径
    ax_path = entry.get("ax_path")
    if ax_path and isinstance(ax_path, list):
        try:
            from ax_poc import capture_ax_tree, node_by_path
            from AppKit import NSScreen
            result = capture_ax_tree(app)
            if not result:
                result = capture_ax_tree("Lark" if "飞书" in app else "飞书")
            if result:
                _, root = result
                node = node_by_path(root, ax_path)
                if node and node.frame:
                    fx, fy, fw, fh = node.frame
                    screen = NSScreen.mainScreen()
                    sh = screen.frame().size.height if screen else 0
                    cx = int(fx + fw / 2)
                    cy_top = int(sh - fy - fh / 2)  # 转左上原点
                    return (cx, cy_top)
        except Exception:
            pass

    return None


def get_vision_description(app: str, action: str) -> Optional[str]:
    """获取供 vision 模型使用的描述"""
    entry = _get_full_entry(app, action)
    if not entry:
        return None
    return entry.get("description") or entry.get("action")


# --- 鼠标位置与点击 ---
def get_mouse_position() -> Optional[Tuple[int, int]]:
    """获取当前鼠标位置（屏幕坐标，原点左上角）"""
    try:
        from AppKit import NSEvent, NSScreen
        loc = NSEvent.mouseLocation()
        screen = NSScreen.mainScreen()
        if screen:
            h = screen.frame().size.height
            y_top = int(h - loc.y)
            return (int(loc.x), y_top)
        return (int(loc.x), int(loc.y))
    except Exception:
        return None


def prompt_user_and_learn(app: str, action: str, description: str = "") -> Optional[Tuple[int, int]]:
    """
    提示用户将鼠标移到目标上并按回车，采集丰富信息并保存
    返回: (x, y) 若成功
    """
    print(f"\n   👆 请将鼠标移动到【{action}】上，然后按回车（我们将记住位置、模板、AX 路径供下次使用）")
    input("   ... 按回车继续 ")
    pos = get_mouse_position()
    if pos:
        save_learned_rich(app, action, pos[0], pos[1], description or action)
        print(f"   ✅ 已记住: ({pos[0]}, {pos[1]}) [含模板、相对位置、AX 路径]")
        return pos
    print("   ⚠️ 无法获取鼠标位置")
    return None


def click_at_position(x: int, y: int, app: str = None) -> bool:
    """在指定坐标执行点击。app 指定时 peekaboo 会加 --app 确保目标应用"""
    try:
        subprocess.run(["cliclick", f"m:{x},{y}", "c:."], check=True, capture_output=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    try:
        cmd = ["peekaboo", "click", "--coords", f"{x},{y}"]
        if app:
            cmd.extend(["--app", app])
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    return False
