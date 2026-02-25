# 小红书 MCP 集成方案（方案 A）

## 一、目标

让 moltbot 通过**和 AI 对话**，或者**发一段文字加图片**，就能帮你把内容发到小红书。

本方案使用 OpenClaw 自带的 mcporter 能力，把小红书工具（xhs-toolkit）接进去，不需要写代码，只需要按步骤配置即可。

---

## 二、整体原理（用人话说）

- **OpenClaw**：moltbot 里的 AI 助手，可以在命令行、飞书、Telegram 等地方和你聊天。
- **mcporter**：OpenClaw 自带的一个小工具，专门用来「按 AI 的意思去调用各种外部工具」。
- **xhs-toolkit**：一个开源的小红书发布工具，能帮你登录小红书、发笔记、发图、加话题。

本方案就是：**把 xhs-toolkit 告诉 mcporter，让 AI 在需要发小红书时，通过 mcporter 去调用 xhs-toolkit**。

你只要用自然语言说「帮我把这段话发到小红书」，AI 就会自动去调用发布功能。

---

## 三、xhs-toolkit 能做什么

| 功能 | 简单说明 |
|------|----------|
| 发布图文 | 发带标题、正文、图片的笔记 |
| 发布视频 | 发视频笔记 |
| 添加话题 | 自动加话题标签，方便被搜索 |
| 登录账号 | 首次需要你手动登录，之后自动记住 |
| 查发布状态 | 看任务有没有发布成功 |
| 数据分析 | 获取账号数据，让 AI 帮你分析 |

---

## 四、需要提前准备的东西

在开始之前，请确认你已经准备好下面这些：

### 4.1 电脑环境

- 已安装 **Google Chrome 浏览器**
- 已安装 **ChromeDriver**（版本要和 Chrome 完全一致，否则会报错）
- 已安装 **Python**（建议 3.9 或以上）
- 已安装 **Node.js**（用于运行 mcporter）

### 4.2 小红书账号

- 需要有一个**小红书创作者中心**的账号
- 首次使用需要你在浏览器里手动登录一次，之后会自动记住

### 4.3 moltbot / OpenClaw

- moltbot 或 OpenClaw 已经能正常运行
- 知道如何通过 `openclaw agent` 或飞书、Telegram 等渠道和 AI 对话

---

## 五、操作步骤（按顺序做）

### 第一步：安装 xhs-toolkit

1. 去 GitHub 把 xhs-toolkit 项目克隆到你电脑的某个目录（比如「我的文档」或「项目」文件夹）
2. 打开终端，进入这个目录
3. 按官方说明安装依赖（推荐用 uv，也可以 pip）
4. 运行状态检查，确保显示「可用」

### 第二步：配置 xhs-toolkit

1. 在 xhs-toolkit 目录里，复制一份环境配置示例文件
2. 打开配置文件，填写：
   - 你电脑上 Chrome 浏览器的路径
   - ChromeDriver 的路径
3. 保存

### 第三步：首次登录小红书

1. 在 xhs-toolkit 目录运行「保存 Cookie」相关命令
2. 会自动弹出一个浏览器窗口
3. 在浏览器里登录你的小红书创作者中心
4. 登录成功后，回到终端按回车，系统会保存登录信息
5. 以后就不用再登了，除非你主动清除

### 第四步：安装 mcporter

用 Node.js 的包管理器全局安装 mcporter，安装完成后在终端输入 `mcporter` 能看到帮助信息即可。

### 第五步：在 mcporter 里添加 xhs-toolkit

**已完成配置**：moltbot 已预置 mcporter 配置：
- 用户级：`~/.mcporter/mcporter.json`
- 项目级：`moltbot/config/mcporter.json`

如果你的 xhs-toolkit 放在其他路径，请编辑上述文件，将 `/Users/oscar/moltbot/xhs-toolkit` 改为实际路径。

### 第六步：在 OpenClaw 里启用 mcporter

1. 打开 OpenClaw 的配置文件
2. 找到 skills 或插件相关配置
3. 确保 mcporter 这一项是启用状态
4. 如果之前没配置过，可以通过运行 OpenClaw 的初始化向导来设置

### 第七步：验证是否成功

1. 启动 OpenClaw 的 gateway（如果还没启动的话）
2. 用 `openclaw agent` 或飞书等渠道，给 AI 发一条消息，例如：「帮我把这句话发到小红书：标题是今日分享，内容是今天天气不错」
3. 如果 AI 能正确调用 xhs-toolkit 并完成发布，说明集成成功

---

## 六、怎么用（日常操作）

### 6.1 只发文字

直接告诉 AI：  
「帮我把这段话发到小红书：标题 XXX，内容 XXX」

AI 会理解你的意思，并调用发布工具。

### 6.2 发文字 + 图片

需要提供图片的**完整路径**，例如：  
「发一篇小红书，标题是美食分享，内容是今天吃了一家很好吃的店，图片在 /Users/xxx/Pictures/food.jpg」

如果你是通过飞书、Telegram 等发图片，系统会先把图片下载到本地，再传给 AI 使用。具体要看 OpenClaw 的媒体处理是否已经配置好。

### 6.3 加话题标签

可以说：  
「发布到小红书，标题 XXX，内容 XXX，话题加：探店、咖啡、周末」

AI 会把话题一并传给发布工具。

---

## 七、关于图片的几个要点

| 方式 | 说明 |
|------|------|
| 本地路径 | 直接告诉 AI 图片在电脑的哪个位置，要写完整路径 |
| 网络链接 | xhs-toolkit 也支持网络图片链接，可以直接用 |
| 飞书 / Telegram 附件 | 需要系统先把附件下载到本地，AI 才能用；一般 OpenClaw 会自动处理，如果发不了可以检查媒体相关配置 |

建议：第一次测试时，先用本地路径的图片，确认能发成功后，再试飞书、Telegram 等渠道的图片。

---

## 八、常见问题速查

**Q：ChromeDriver 版本不对怎么办？**  
在 Chrome 里打开「关于」或版本页面，记下版本号，再去下载和这个版本完全一致的 ChromeDriver，并更新到 xhs-toolkit 的配置里。

**Q：首次登录为什么要弹浏览器？**  
因为需要你在真实页面里完成验证（如扫码、输验证码）。登录成功后，系统会保存 Cookie，下次就不用再登了。

**Q：mcporter 配置文件在哪？**  
一般在 `config/mcporter.json`，具体位置要看你的项目或用户目录结构。可以查阅 mcporter 的官方文档。

**Q：发图失败怎么办？**  
先确认：  
1）图片路径是否正确；  
2）xhs-toolkit 是否已正常登录；  
3）Chrome 和 ChromeDriver 是否都能正常运行。

---

## 九、参考链接

- xhs-toolkit 项目：https://github.com/aki66938/xhs-toolkit  
- xhs-toolkit MCP 说明：https://playbooks.com/mcp/aki66938/xhs-toolkit  
- mcporter：https://mcporter.dev  
- OpenClaw 文档：https://docs.openclaw.ai  
