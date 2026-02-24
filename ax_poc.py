#!/usr/bin/env python3
"""
AX 语义树 POC - 小规模验证
基于 macOS Accessibility API 实现：抓取 AX 树、语义查询、执行操作
"""

import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

# macOS 原生依赖（系统自带）
import ApplicationServices
from AppKit import NSWorkspace

# AX 操作常量
AX_ACTION_PRESS = "AXPress"
AX_ACTION_INCREMENT = "AXIncrement"
AX_ACTION_DECREMENT = "AXDecrement"


@dataclass
class AXNode:
    """AX 语义节点"""
    role: str
    title: str
    value: Optional[str]
    frame: Optional[Tuple[float, float, float, float]]  # x, y, w, h
    element_ref: Any  # 内部使用，不序列化
    children: List["AXNode"]

    def to_dict(self) -> Dict:
        d = {
            "role": self.role,
            "title": self.title or "",
            "value": self.value or "",
            "frame": self.frame,
            "children": [c.to_dict() for c in self.children]
        }
        return d


def _get_attr(element, attr: str, default=None):
    """安全获取 AX 属性"""
    err, val = ApplicationServices.AXUIElementCopyAttributeValue(element, attr, None)
    if err == 0 and val is not None:
        return val
    return default


def _get_frame(element) -> Optional[Tuple[float, float, float, float]]:
    """获取控件坐标 (x, y, width, height)"""
    val = _get_attr(element, "AXFrame")
    if val is not None:
        try:
            if hasattr(val, 'origin') and hasattr(val, 'size'):
                return (
                    float(val.origin.x), float(val.origin.y),
                    float(val.size.width), float(val.size.height)
                )
            # 某些环境下可能是 tuple/dict
            if isinstance(val, (list, tuple)) and len(val) >= 4:
                return tuple(float(v) for v in val[:4])
        except Exception:
            pass
    return None


def _str_attr(val) -> str:
    """将 AX 属性转为字符串"""
    if val is None:
        return ""
    if hasattr(val, '__class__') and 'CFType' in str(type(val)):
        return str(val) if val else ""
    return str(val)


def _build_ax_tree(element, depth: int, max_depth: int = 8) -> Optional[AXNode]:
    """递归构建 AX 树"""
    if depth > max_depth:
        return None

    role = _get_attr(element, "AXRole")
    title = _get_attr(element, "AXTitle")
    value = _get_attr(element, "AXValue")
    desc = _get_attr(element, "AXDescription")  # 部分控件用此表示
    help_attr = _get_attr(element, "AXHelp")

    if role is None:
        role = "AXUnknown"

    role = _str_attr(role)
    title = _str_attr(title) or _str_attr(desc) or _str_attr(help_attr)
    value = _str_attr(value)

    frame = _get_frame(element)

    children = []
    err, child_vals = ApplicationServices.AXUIElementCopyAttributeValue(element, "AXChildren", None)
    if err == 0 and child_vals:
        for child in child_vals:
            child_node = _build_ax_tree(child, depth + 1, max_depth)
            if child_node:
                children.append(child_node)

    return AXNode(
        role=str(role),
        title=str(title) if title else "",
        value=str(value) if value else "",
        frame=frame,
        element_ref=element,
        children=children
    )


def capture_ax_tree(app_name: str) -> Optional[Tuple[Any, AXNode]]:
    """
    抓取指定应用的 AX 语义树
    返回: (ax_app_ref, root_node) 或 None
    """
    workspace = NSWorkspace.sharedWorkspace()
    apps = workspace.runningApplications()

    for app in apps:
        name = app.localizedName() or ""
        if app_name in name or name in app_name:
            if "helper" in name.lower():
                continue

            pid = app.processIdentifier()
            ax_app = ApplicationServices.AXUIElementCreateApplication(pid)

            err, windows = ApplicationServices.AXUIElementCopyAttributeValue(ax_app, "AXWindows", None)
            if err != 0 or not windows:
                continue

            # 取主窗口（通常是第一个）
            for win in windows:
                node = _build_ax_tree(win, 0)
                if node:
                    return (ax_app, node)

    return None


def semantic_query(node: AXNode, role: Optional[str] = None, title: Optional[str] = None,
                  title_contains: Optional[str] = None) -> List[AXNode]:
    """
    语义查询：在 AX 树中查找匹配的节点
    - role: 精确匹配（如 "AXButton", "AXTextField"）
    - title: 精确匹配标题
    - title_contains: 标题包含（模糊匹配）
    """
    results = []

    def search(n: AXNode):
        match = True
        if role and n.role != role:
            match = False
        if title and n.title != title:
            match = False
        if title_contains and title_contains not in n.title:
            match = False
        if match and (n.role or n.title):  # 至少有一个可识别属性
            results.append(n)
        for c in n.children:
            search(c)

    search(node)
    return results


def ax_perform_action(node: AXNode, action: str = AX_ACTION_PRESS) -> bool:
    """
    对 AX 节点执行操作
    action: AXPress, AXIncrement, AXDecrement 等
    """
    err = ApplicationServices.AXUIElementPerformAction(node.element_ref, action)
    return err == 0  # kAXErrorSuccess = 0


def ax_set_value(node: AXNode, value: str) -> bool:
    """设置输入框等控件的值"""
    err = ApplicationServices.AXUIElementSetAttributeValue(node.element_ref, "AXValue", value)
    return err == 0


def ax_click_by_frame(node: AXNode) -> bool:
    """
    若 AXPress 失败，尝试通过坐标点击（回退到 peekaboo/cliclick）
    """
    if not node.frame:
        return False
    x, y, w, h = node.frame
    click_x = x + w / 2
    click_y = y + h / 2

    import subprocess
    # 优先 cliclick
    try:
        subprocess.run(['cliclick', f'm:{int(click_x)},{int(click_y)}', 'c:.'], check=True, capture_output=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    try:
        subprocess.run(['peekaboo', 'click', '--coords', f'{int(click_x)},{int(click_y)}'],
                      check=True, capture_output=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass
    return False


def find_element_at_point(node: AXNode, x: int, y: int, path: List[int] = None) -> Optional[List[int]]:
    """
    在 AX 树中查找包含 (x,y) 的最深层元素
    点的坐标应为左上原点（与截图一致）
    返回: 路径 [子节点索引, ...] 或 None
    """
    path = path or []
    if not node.frame:
        return None
    try:
        from AppKit import NSScreen
        screen = NSScreen.mainScreen()
        sh = float(screen.frame().size.height) if screen else 0
    except Exception:
        return None

    fx, fy, fw, fh = node.frame
    # AXFrame 为 Cocoa 坐标（原点左下），转为左上原点
    fy_top = sh - fy - fh
    if not (fx <= x <= fx + fw and fy_top <= y <= fy_top + fh):
        return None

    for i, child in enumerate(node.children):
        found = find_element_at_point(child, x, y, path + [i])
        if found is not None:
            return found
    return path


def node_by_path(node: AXNode, path: List[int]) -> Optional[AXNode]:
    """按路径索引获取 AX 节点"""
    current = node
    for idx in path:
        if idx >= len(current.children):
            return None
        current = current.children[idx]
    return current


def dump_tree_to_json(node: AXNode) -> str:
    """将 AX 树导出为 JSON（不包含 element_ref）"""
    def _serialize(n: AXNode) -> Dict:
        return {
            "role": n.role,
            "title": n.title,
            "value": n.value or "",
            "frame": list(n.frame) if n.frame else None,
            "children": [_serialize(c) for c in n.children]
        }
    return json.dumps(_serialize(node), ensure_ascii=False, indent=2)


# --- 便捷封装 ---

def find_and_click(app_name: str, role: str = "AXButton", title: str = None,
                   title_contains: str = None) -> Tuple[bool, str]:
    """
    查找并点击控件
    返回: (成功, 消息)
    """
    result = capture_ax_tree(app_name)
    if not result:
        return False, f"未找到应用或无法获取 AX 树: {app_name}"

    _, root = result
    nodes = semantic_query(root, role=role, title=title, title_contains=title_contains)

    if not nodes:
        return False, f"未找到匹配控件: role={role}, title={title}, title_contains={title_contains}"

    node = nodes[0]
    # 优先 AXPress
    if ax_perform_action(node, AX_ACTION_PRESS):
        return True, f"AX 点击成功: {node.title or node.role}"
    # 回退坐标点击
    if ax_click_by_frame(node):
        return True, f"坐标点击成功: {node.title or node.role}"
    return False, "AX 操作失败且坐标点击失败"


def find_and_type(app_name: str, text: str, role: str = "AXTextField",
                  title: str = None, title_contains: str = None) -> Tuple[bool, str]:
    """
    查找输入框并输入文本
    """
    result = capture_ax_tree(app_name)
    if not result:
        return False, f"未找到应用: {app_name}"

    _, root = result
    nodes = semantic_query(root, role=role, title=title, title_contains=title_contains)

    if not nodes:
        return False, f"未找到输入框: role={role}, title={title}, title_contains={title_contains}"

    node = nodes[0]
    if ax_set_value(node, text):
        return True, f"AX 输入成功: {text[:20]}..."
    return False, "AX 输入失败"


if __name__ == "__main__":
    # 简单测试：抓取飞书 AX 树并打印
    print("=== AX 语义树 POC 测试 ===\n")

    for app in ["飞书", "Lark"]:
        print(f"尝试应用: {app}")
        result = capture_ax_tree(app)
        if result:
            _, root = result
            print(f"✅ 成功抓取 AX 树")
            # 查找按钮
            buttons = semantic_query(root, role="AXButton", title_contains="发送")
            print(f"找到 {len(buttons)} 个包含'发送'的按钮")
            for b in buttons[:5]:
                print(f"  - {b.role} '{b.title}' frame={b.frame}")
            break
    else:
        print("❌ 未找到飞书/Lark，请确保应用已打开")
