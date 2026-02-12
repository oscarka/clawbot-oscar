
from AppKit import NSWorkspace

def list_running_apps():
    workspace = NSWorkspace.sharedWorkspace()
    apps = workspace.runningApplications()
    
    print(f"📦 Total Running Apps: {len(apps)}")
    print("-" * 40)
    for app in apps:
        name = app.localizedName()
        pid = app.processIdentifier()
        bundle = app.bundleIdentifier()
        
        # Filter out obvious system daemons to reduce noise, but keep "Lark" related ones
        if app.activationPolicy() == 0: # 0 = Regular App (Active in Dock)
            print(f"APP: {name} | PID: {pid} | ID: {bundle}")
        elif "lark" in (name or "").lower() or "feishu" in (name or "").lower():
             print(f"BG:  {name} | PID: {pid} | ID: {bundle}")

if __name__ == "__main__":
    list_running_apps()
