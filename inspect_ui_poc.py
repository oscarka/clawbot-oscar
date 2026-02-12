
import Quartz
import ApplicationServices
from AppKit import NSWorkspace
import time

def get_ax_ui_element(pid):
    """通过 PID 获取应用的 Accessibility 对象"""
    app_ref = ApplicationServices.AXUIElementCreateApplication(pid)
    return app_ref

def inspect_app(app_name="飞书"): # Targeted explicitly
    workspace = NSWorkspace.sharedWorkspace()
    apps = workspace.runningApplications()
    
    candidate_apps = []
    for app in apps:
        name = app.localizedName() or ""
        # Precise matching for the main process
        if app_name == name:
            candidate_apps.append(app)
            
    if not candidate_apps:
        print(f"❌ 未找到包含 '{app_name}' 的运行进程")
        return

    print(f"🔍 找到 {len(candidate_apps)} 个候选进程: {[app.localizedName() for app in candidate_apps]}")

    target_found = False

    # 递归遍历 (深度优先，只打印前几层避免刷屏)
    def traverse(element, depth=0, max_depth=3):
        if depth > max_depth: return
        
        # 获取角色和标题
        err, role = ApplicationServices.AXUIElementCopyAttributeValue(element, "AXRole", None)
        err, title = ApplicationServices.AXUIElementCopyAttributeValue(element, "AXTitle", None)
        err, frame = ApplicationServices.AXUIElementCopyAttributeValue(element, "AXFrame", None) # 核心：真实坐标
        
        indent = "  " * depth
        
        # 为了简洁，只打印标题不为空或者角色是窗口/按钮的元素
        if title or role in ["AXWindow", "AXButton", "AXTextField"]:
            info = f"{indent}- [{role}] '{title}'"
            if role == "AXButton":
                info += f" 🎯 BOUNDS: {frame}"
            print(info)
        
        # 获取子元素
        err, children = ApplicationServices.AXUIElementCopyAttributeValue(element, "AXChildren", None)
        if children:
            for child in children: # 打印所有子节点
                traverse(child, depth + 1, max_depth)

    for app in candidate_apps:
        print(f"\n👉 尝试连接: {app.localizedName()} (PID: {app.processIdentifier()})...")
        
        # 排除明显的 Helper
        if "helper" in (app.localizedName() or "").lower():
            print("   ⚠️ 跳过 Helper 进程")
            continue

        # 获取 AX 对象
        ax_app = get_ax_ui_element(app.processIdentifier())
        
        # 获取窗口列表
        error, windows = ApplicationServices.AXUIElementCopyAttributeValue(
            ax_app, "AXWindows", None
        )
        
        if error != 0:
            print(f"   ❌ 无法获取窗口 (Error Code: {error}) - 可能因为无权限，或者应用还没加载UI")
            continue
            
        if not windows:
            print("   ⚠️  无可见窗口 (可能是后台进程)")
            continue
            
        print(f"   ✅ 成功发现 {len(windows)} 个窗口！")
        target_found = True
        
        # 遍历主窗口
        print("\n   🔍 分析主窗口结构:")
        for w in windows:
            traverse(w)
        break # 找到主窗口后退出
    
    if not target_found:
        print("\n❌ 所有尝试均失败。可能原因：")
        print("1. 确实没有打开主窗口")
        print("2. 权限仍然被系统拦截 (TCC 需要重置)")

if __name__ == "__main__":
    # 尝试中文名
    inspect_app("飞书")
