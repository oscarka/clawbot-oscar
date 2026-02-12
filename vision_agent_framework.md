# 视觉引导的 AI 自动化系统架构

## 核心概念

将 macOS 视觉控制能力与 AI 模型结合，实现**视觉反馈闭环**的自动化任务执行。

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                   用户指令                                │
│  "帮我做一个 Excel 表格并通过飞书发送给张三"            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              AI 任务规划器 (Claude/GPT)                  │
│  - 分解任务为步骤                                        │
│  - 识别需要的应用和操作                                   │
│  - 生成执行计划                                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           视觉感知层 (Peekaboo + AI Vision)              │
│  - 截图当前屏幕                                          │
│  - AI 识别当前状态（应用、窗口、UI元素）                 │
│  - 定位目标元素（按钮、输入框、菜单等）                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           执行层 (macOS 原生 + Peekaboo)                 │
│  - 点击、输入、滚动、拖拽                                 │
│  - 应用切换、窗口管理                                     │
│  - 文件操作                                              │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│           验证层 (视觉反馈)                               │
│  - 截图验证操作结果                                      │
│  - AI 判断是否成功/需要调整                               │
│  - 错误检测和恢复                                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
              ┌─────────┐
              │ 完成？  │
              └────┬────┘
                   │ 否
                   ▼
            ┌──────────────┐
            │ 继续下一步骤  │
            └──────────────┘
```

## 技术栈

### 1. 视觉感知
- **Peekaboo**: macOS UI 自动化
- **GLM-4.6v-flash**: 视觉理解（免费、快速）
- **Claude/GPT-4V**: 复杂场景理解

### 2. 任务规划
- **Claude Opus**: 任务分解和规划
- **OpenClaw Gateway**: 任务编排和执行

### 3. 执行控制
- **macOS Accessibility API**: 原生控制
- **AppleScript**: 应用级操作
- **Peekaboo**: UI 元素操作

### 4. 反馈验证
- **实时截图**: 操作前后对比
- **AI 状态识别**: 判断操作是否成功
- **错误恢复**: 自动重试和调整

## 实现示例：Excel + 飞书发送

### 任务分解

```
1. 打开 Excel (Numbers/Excel)
2. 创建新表格
3. 输入数据
4. 保存文件
5. 打开飞书
6. 找到联系人"张三"
7. 发送文件
8. 验证发送成功
```

### 代码框架

```python
class VisionAgent:
    def __init__(self):
        self.vision_model = "glm-4.6v-flash"  # 视觉理解
        self.planning_model = "claude-opus"    # 任务规划
        self.screenshot_dir = "/tmp/vision_agent"
        
    def plan_task(self, user_request):
        """使用 AI 规划任务步骤"""
        prompt = f"""
        用户请求：{user_request}
        
        请分解为具体步骤，每个步骤包括：
        - 操作类型（打开应用、点击、输入、等待等）
        - 目标（应用名、UI元素、内容）
        - 预期结果
        """
        # 调用 Claude 规划
        return steps
        
    def perceive_state(self):
        """感知当前屏幕状态"""
        screenshot = self.capture_screen()
        state = self.vision_analyze(screenshot)
        return {
            "active_app": state.app_name,
            "ui_elements": state.elements,
            "current_state": state.description
        }
        
    def execute_step(self, step):
        """执行单个步骤"""
        # 1. 感知当前状态
        current_state = self.perceive_state()
        
        # 2. 定位目标元素
        target = self.locate_target(step.target, current_state)
        
        # 3. 执行操作
        result = self.perform_action(step.action, target)
        
        # 4. 验证结果
        success = self.verify_result(step.expected_result)
        
        return success
        
    def run_task(self, user_request):
        """执行完整任务"""
        steps = self.plan_task(user_request)
        
        for step in steps:
            success = False
            retries = 0
            
            while not success and retries < 3:
                success = self.execute_step(step)
                if not success:
                    # 分析失败原因并调整
                    self.adjust_strategy(step)
                    retries += 1
                    
            if not success:
                # 请求人工干预
                self.request_help(step)
                break
```

## 与 Cursor 监控的相似性

### Cursor 监控模式
```
监控 → 截图 → AI 分析 → 判断问题 → 通知用户 → 等待指令 → 执行操作
```

### 通用自动化模式
```
用户指令 → AI 规划 → 截图感知 → 执行操作 → 验证结果 → 继续/调整
```

## 优势

1. **无需 API 集成** - 通过 UI 操作，支持任何应用
2. **视觉反馈闭环** - 实时验证，自动调整
3. **通用性强** - 不限于特定应用
4. **智能错误处理** - AI 识别问题并恢复

## 挑战

1. **UI 变化** - 应用更新可能破坏自动化
2. **性能** - 截图和 AI 分析需要时间
3. **可靠性** - 需要大量测试和错误处理
4. **权限** - 需要屏幕录制和辅助功能权限

## 下一步

1. 创建基础框架
2. 实现简单的任务（如"打开应用并点击按钮"）
3. 逐步扩展到复杂任务
4. 集成到 OpenClaw 作为 Skill
