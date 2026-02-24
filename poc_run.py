#!/usr/bin/env python3
"""
桌面 AI POC - 小规模验证
验证：AX 优先 + 视觉回退 是否可行

测试流程：用飞书发送一条消息给文件助手
- 步骤 1: 确保飞书已打开，并处于聊天界面
- 步骤 2: 在输入框输入 "POC测试"
- 步骤 3: 点击发送按钮
"""

import sys
import time
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from learned_positions import (
    find_using_learned,
    save_learned_rich,
    prompt_user_and_learn,
    click_at_position,
)
from ax_poc import (
    capture_ax_tree,
    semantic_query,
    ax_perform_action,
    ax_set_value,
    ax_click_by_frame,
    AX_ACTION_PRESS,
    dump_tree_to_json,
)


def _capture_for_app(app: str = "Lark"):
    """截取主屏（避免多显示器时截错屏）"""
    import subprocess
    from pathlib import Path
    path = f"/tmp/vision_{app}_{int(__import__('time').time())}.png"
    r = subprocess.run(
        ["peekaboo", "image", "--mode", "screen", "--screen-index", "0", "--path", path],
        capture_output=True, timeout=10
    )
    return path if r.returncode == 0 and Path(path).exists() else None


def vision_fallback_click(target_desc: str) -> tuple:
    """视觉回退：截图 + AI 定位 + 坐标点击
    返回: (成功, 点击坐标或None)
    """
    try:
        from vision_agent import VisionAgent
        from learned_positions import _to_click_coords
        agent = VisionAgent()
        screenshot = _capture_for_app("Lark") or agent.capture_screen()
        if not screenshot:
            print("   ⚠️ 视觉回退: 截图失败")
            return False, None

        state = {"screenshot": screenshot}
        located = agent.locate_element(target_desc, state)
        if not located or not located.get("found"):
            print("   ⚠️ 视觉回退: 未定位到目标")
            return False, None

        coords = located.get("coordinates", {})
        x, y = coords.get("x"), coords.get("y")
        if x is None or y is None:
            print("   ⚠️ 视觉回退: 无有效坐标")
            return False, None

        # 坐标转换（若截图非 1x）
        x_click, y_click = _to_click_coords(x, y, screenshot)
        located = {**located, "coordinates": {"x": x_click, "y": y_click}, "_click_app": "Lark"}
        print(f"   📍 视觉定位: ({x}, {y}) → 点击 ({x_click}, {y_click}) [--app Lark]")
        ok = agent.perform_action("click", located)
        return ok, (x_click, y_click) if ok else None
    except Exception as e:
        print(f"   ⚠️ 视觉回退异常: {e}")
        return False, None


def vision_fallback_type(text: str) -> tuple:
    """视觉回退：定位输入框 → 点击聚焦 → 输入（Retina 转换）"""
    try:
        from vision_agent import VisionAgent
        from learned_positions import _to_click_coords
        agent = VisionAgent()
        screenshot = _capture_for_app("Lark") or agent.capture_screen()
        if not screenshot:
            return False, None
        state = {"screenshot": screenshot}
        located = agent.locate_element("底部或中间的文本输入框，用于输入消息", state)
        if not located or not located.get("found"):
            return False, None
        coords = located.get("coordinates", {})
        x, y = coords.get("x"), coords.get("y")
        if x is None or y is None:
            return False, None
        # 坐标转换
        x_click, y_click = _to_click_coords(x, y, screenshot)
        located = {**located, "coordinates": {"x": x_click, "y": y_click}, "_click_app": "Lark"}
        print(f"   📍 输入框: ({x}, {y}) → 点击 ({x_click}, {y_click}) [--app Lark]")
        # 先点击聚焦，再输入
        if not agent.perform_action("click", located):
            return False, None
        time.sleep(0.3)
        ok = agent.perform_action("type", located, content=text)
        return ok, (x_click, y_click) if ok else None
    except Exception as e:
        print(f"   ⚠️ 视觉回退异常: {e}")
        return False, None


def step1_ensure_lark_ready() -> bool:
    """步骤 0: 打开飞书（若未运行）、激活置前、确保 AX 可访问"""
    import subprocess

    result = capture_ax_tree("飞书")
    if not result:
        result = capture_ax_tree("Lark")
    if not result:
        print("📱 飞书未运行，正在打开...")
        for name in ["Lark", "飞书"]:
            r = subprocess.run(["open", "-a", name], capture_output=True)
            if r.returncode == 0:
                print(f"   ✅ 已启动 {name}")
                time.sleep(3)  # 等待应用加载
                break
        result = capture_ax_tree("飞书")
        if not result:
            result = capture_ax_tree("Lark")
    if not result:
        print("❌ 无法连接飞书 AX 树，请检查：1) 辅助功能权限 2) 飞书是否已启动")
        return False
    # 激活飞书，自动置前
    for name in ["Lark", "飞书"]:
        subprocess.run(["open", "-a", name], capture_output=True)
        time.sleep(0.5)
        break
    print("✅ 飞书已就绪并置前，AX 树可访问")
    return True


def step2_type_message(text: str = "POC测试") -> tuple:
    """步骤 1: 在输入框输入消息（缓存 > AX > 视觉 > 人机学习）"""
    print(f"\n📝 步骤: 输入消息 '{text}'")
    app_norm = "飞书"

    # 1. 优先使用已学习的输入框位置
    found = find_using_learned(app_norm, "输入框")
    if found:
        print(f"   📎 使用已记住的输入框位置: {found}")
        if click_at_position(*found, app="Lark"):
            time.sleep(0.3)
            import subprocess
            try:
                subprocess.run(["cliclick", f"t:{text}"], check=True, capture_output=True)
            except Exception:
                subprocess.run(["peekaboo", "type", text, "--delay", "10"], capture_output=True)
            print("   ✅ 缓存输入成功")
            return True, "cache"

    result = capture_ax_tree("飞书")
    if not result:
        result = capture_ax_tree("Lark")
    if not result:
        return False, "应用未找到"

    _, root = result
    # 2. 查找输入框：AXTextField, AXTextArea, 或包含"输入"等
    nodes = semantic_query(root, role="AXTextField")
    nodes += semantic_query(root, role="AXTextArea")
    nodes += semantic_query(root, title_contains="输入")
    nodes += semantic_query(root, title_contains="消息")

    for node in nodes:
        if node.frame and node.frame[2] > 50 and node.frame[3] > 20:  # 合理大小的输入框
            if ax_set_value(node, text):
                print("   ✅ AX 输入成功")
                return True, "AX"
            if ax_click_by_frame(node):
                time.sleep(0.3)
                import subprocess
                try:
                    subprocess.run(["cliclick", f"t:{text}"], check=True, capture_output=True)
                except Exception:
                    subprocess.run(["peekaboo", "type", text, "--delay", "10"], capture_output=True)
                print("   ✅ 坐标点击+输入成功")
                return True, "AX+coord"

    # 3. 视觉回退
    print("   ⚠️ AX 未找到输入框，尝试视觉回退...")
    ok, coords = vision_fallback_type(text)
    if ok:
        if coords:
            save_learned_rich(app_norm, "输入框", coords[0], coords[1], "底部或中间的文本输入框，用于输入消息", from_vision=True)
            print("   ✅ 视觉回退输入成功，已记住输入框位置")
        else:
            print("   ✅ 视觉回退输入成功")
        return True, "vision"
    # 4. 人机配合
    learned = prompt_user_and_learn(app_norm, "输入框", "底部或中间的文本输入框，用于输入消息")
        if learned and click_at_position(*learned, app="Lark"):
            time.sleep(0.3)
            import subprocess
            try:
                subprocess.run(["cliclick", f"t:{text}"], check=True, capture_output=True)
            except Exception:
                subprocess.run(["peekaboo", "type", text, "--delay", "10"], capture_output=True)
            return True, "learned"
    return False, "失败"


def step3_click_send() -> tuple:
    """步骤 2: 点击发送按钮（缓存 > AX > 视觉 > 人机配合学习）"""
    print("\n📤 步骤: 点击发送按钮")
    app = "飞书"

    result = capture_ax_tree(app)
    if not result:
        result = capture_ax_tree("Lark")
        app = "Lark"
    if not result:
        return False, "应用未找到"

    # 1. 优先使用已学习的位置
    app_norm = "飞书"  # 飞书/Lark 统一
    found = find_using_learned(app_norm, "发送")
    if found:
        print(f"   📎 使用已记住的位置: {found}")
        if click_at_position(*found, app="Lark"):
            print("   ✅ 缓存点击成功")
            return True, "cache"

    _, root = result
    # 2. 尝试 AX 语义匹配
    nodes = semantic_query(root, role="AXButton", title_contains="发送")
    if not nodes:
        nodes = semantic_query(root, title_contains="发送")

    # 飞书等 Electron：无语义匹配时先尝试 peekaboo 按文本点击，再视觉
    if not nodes:
        print("   ⚠️ AX 无语义匹配...")
        # 优先尝试 peekaboo 按文本点击（更可靠）
        import subprocess
        r = subprocess.run(["peekaboo", "click", "发送", "--app", "Lark"], capture_output=True, timeout=10)
        if r.returncode == 0:
            print("   ✅ peekaboo 按文本点击成功")
            return True, "peekaboo"
        ok, coords = vision_fallback_click("蓝色的发送按钮，纸飞机形状，在输入框右侧")
        if ok and coords:
            save_learned_rich(app_norm, "发送", coords[0], coords[1], "蓝色的发送按钮，纸飞机形状，在输入框右侧", from_vision=True)
            print("   ✅ 视觉定位成功，已记住供下次使用")
            return True, "vision"
        # 视觉也失败：人机配合，请用户指认
        learned = prompt_user_and_learn(app_norm, "发送", "蓝色的发送按钮，纸飞机形状，在输入框右侧")
        if learned and click_at_position(*learned, app="Lark"):
            return True, "learned"
        return False, "失败"

    # 3. AX 有匹配，尝试执行
    for node in nodes:
        if ax_perform_action(node, AX_ACTION_PRESS):
            print("   ✅ AX 点击成功")
            return True, "AX"
        if ax_click_by_frame(node):
            print("   ✅ 坐标点击成功")
            return True, "AX+coord"

    # 4. AX 执行失败，走视觉回退
    print("   ⚠️ AX 执行失败，尝试视觉回退...")
    ok, coords = vision_fallback_click("蓝色的发送按钮，纸飞机形状，在输入框右侧")
    if ok and coords:
        save_learned_rich(app_norm, "发送", coords[0], coords[1], "蓝色的发送按钮，纸飞机形状，在输入框右侧", from_vision=True)
        print("   ✅ 视觉回退成功，已记住供下次使用")
        return True, "vision"
    # 5. 视觉也失败：人机配合
    learned = prompt_user_and_learn(app_norm, "发送", "蓝色的发送按钮，纸飞机形状，在输入框右侧")
    if learned and click_at_position(*learned, app="Lark"):
        return True, "learned"
    return False, "失败"


def run_full_poc():
    """运行完整 POC 流程"""
    print("=" * 50)
    print("桌面 AI POC - AX 优先 + 视觉回退 验证")
    print("=" * 50)
    print("\n流程: 自动打开飞书（若未运行）→ 输入 POC测试 → 点击发送")
    input("按回车开始...")

    results = []

    if not step1_ensure_lark_ready():
        print("\n❌ POC 终止")
        return

    # 步骤 1: 输入
    ok1, method1 = step2_type_message("POC测试")
    results.append(("输入消息", ok1, method1))
    time.sleep(1)

    # 步骤 2: 发送
    ok2, method2 = step3_click_send()
    results.append(("点击发送", ok2, method2))

    # 汇总
    print("\n" + "=" * 50)
    print("POC 结果汇总")
    print("=" * 50)
    for name, ok, method in results:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}: {method}")
    all_ok = all(r[1] for r in results)
    print(f"\n总体: {'✅ 通过' if all_ok else '❌ 未完全通过'}")


def run_ax_only_test():
    """仅测试 AX 树抓取与语义查询（不执行操作）"""
    print("=" * 50)
    print("AX 树抓取与语义查询测试")
    print("=" * 50)

    for app in ["飞书", "Lark"]:
        result = capture_ax_tree(app)
        if result:
            _, root = result
            print(f"\n✅ 成功抓取 {app} 的 AX 树\n")

            # 保存到文件
            out_path = Path("/tmp/ax_tree_poc.json")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(dump_tree_to_json(root))
            print(f"已保存到 {out_path}\n")

            # 语义查询演示
            buttons = semantic_query(root, title_contains="发送")
            print(f"包含'发送'的控件: {len(buttons)} 个")
            for b in buttons[:5]:
                print(f"  - {b.role} '{b.title}' frame={b.frame}")

            inputs = semantic_query(root, role="AXTextField") + semantic_query(root, role="AXTextArea")
            print(f"\n输入框 (AXTextField/AXTextArea): {len(inputs)} 个")
            for i in inputs[:5]:
                print(f"  - {i.role} '{i.title}' frame={i.frame}")

            return
    print("❌ 未找到飞书/Lark，请确保应用已打开")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ax-only", action="store_true", help="仅测试 AX 树抓取，不执行操作")
    parser.add_argument("--full", action="store_true", help="运行完整 POC 流程")
    parser.add_argument("--clear-learned", action="store_true", help="清除已学习的位置缓存后运行")
    args = parser.parse_args()

    if args.clear_learned:
        from learned_positions import CACHE_FILE
        if CACHE_FILE.exists():
            CACHE_FILE.unlink()
            print(f"已清除 {CACHE_FILE}")
        else:
            print("无缓存可清除")

    if args.ax_only:
        run_ax_only_test()
    else:
        run_full_poc()
