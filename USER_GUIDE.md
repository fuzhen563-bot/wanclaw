# WanClaw 使用手册

> WanClaw（万爪）— 企业级 AI 桌面助手，支持自然语言控制电脑、20+ IM 平台接入、浏览器 RPA、跨平台部署

---

## 目录

1. [概述](#1-概述)
2. [安装部署](#2-安装部署)
3. [快速配置](#3-快速配置)
4. [桌面助手（WebUI）](#4-桌面助手webui)
5. [桌面自动化](#5-桌面自动化)
6. [跨平台操作](#6-跨平台操作)
7. [IM 平台接入](#7-im-平台接入)
8. [AI 引擎配置](#8-ai-引擎配置)
9. [技能系统](#9-技能系统)
10. [向量记忆](#10-向量记忆)
11. [浏览器 RPA](#11-浏览器-rpa)
12. [安全机制](#12-安全机制)
13. [API 参考](#13-api-参考)
14. [运维管理](#14-运维管理)
15. [故障排查](#15-故障排查)

---

## 1. 概述

### 1.1 核心能力

WanClaw 是一款企业级 AI 桌面助手，核心功能包括：

| 能力 | 说明 |
|------|------|
| **自然语言控制** | 通过 WebUI 或 IM 发送自然语言，AI 自动解析并执行电脑操作 |
| **桌面自动化** | 鼠标、键盘、截图、OCR 识别、视觉定位 |
| **IM 聚合** | 20+ 平台统一接入（企微、飞书、钉钉、Telegram 等） |
| **浏览器 RPA** | Playwright + Selenium 双引擎网页自动化 |
| **办公自动化** | Excel/Word/PDF 文档处理 |
| **向量记忆** | LanceDB 语义搜索，记住用户偏好和对话历史 |
| **工作流编排** | DAG 可视化编排、定时任务、条件分支 |
| **跨平台窗口管理** | pywin32 / AppKit / wnck 全系统 API |
| **安全启动器** | 白名单应用启动，无 subprocess |

### 1.2 系统架构

```
┌──────────────────────────────────────────────────────┐
│                     用户交互层                         │
│    WebUI (桌面助手)  │  IM 消息  │  API 调用         │
└──────────────────────┬───────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────┐
│                    WanClaw Gateway                    │
│               FastAPI + WebSocket (8000)              │
└──────────────────────┬───────────────────────────────┘
                       ↓
        ┌─────────────┼─────────────┐
        ↓             ↓             ↓
   ┌─────────┐  ┌──────────┐  ┌──────────┐
   │  Agent  │  │  Skills  │  │  IM适配器 │
   │ (ReAct) │  │ (27+)    │  │  (20+)    │
   └────┬────┘  └────┬─────┘  └────┬─────┘
        ↓             ↓             ↓
   ┌────────────────────────────────────────┐
   │              自动化执行层               │
   │  InputController │ AppLauncher │ RPA    │
   │  WindowManager  │  OCR        │ 文档处理 │
   └────────────────────────────────────────┘
        ↓             ↓             ↓
   ┌─────────┐  ┌──────────┐  ┌──────────┐
   │ PyAutoGUI│  │ Playwright│  │ openpyxl │
   │ (系统API)│  │ (浏览器)  │  │ (文档)   │
   └─────────┘  └──────────┘  └──────────┘
```

---

## 2. 安装部署

### 2.1 环境要求

| 项目 | 最低要求 | 推荐 |
|------|---------|------|
| Python | 3.8+ | 3.10+ |
| 内存 | 2 GB | 4 GB+ |
| 磁盘 | 5 GB | 20 GB+ |
| 系统 | Linux/macOS/Windows | Linux (Ubuntu 20.04+) |

### 2.2 安装方式

#### 方式一：一键安装（推荐）

```bash
curl -fsSL https://raw.githubusercontent.com/wanclaw/wanclaw/main/install.sh | bash
```

#### 方式二：手动安装

```bash
# 克隆代码
git clone https://github.com/fuzhen563-bot/wanclaw.git
cd wanclaw

# 安装依赖
pip install -r dist/requirements.txt

# 运行
python -m wanclaw.main
```

#### 方式三：Docker 部署

```bash
cd wanclaw/dist
docker-compose up -d
```

#### 方式四：Windows 原生运行

```powershell
# PowerShell
git clone https://github.com/fuzhen563-bot/wanclaw.git
cd wanclaw
pip install -r dist/requirements.txt
python -m wanclaw.main
```

### 2.3 安装后访问

| 服务 | 地址 | 默认密码 |
|------|------|---------|
| 管理后台 | `http://localhost:8000/admin` | `wanclaw` |
| API 文档 | `http://localhost:8000/docs` | - |
| 首页 | `http://localhost:8000/` | - |

---

## 3. 快速配置

### 3.1 AI 模型配置

登录管理后台后，进入 **AI 引擎** 页面，选择 AI 提供商并填入 API Key：

```yaml
# 可选 AI 提供商
- Ollama      # 本地部署，零成本
- DeepSeek    # 高性价比（推荐）
- 通义千问    # 中文最强
- 智谱 GLM    # 免费额度
- Moonshot   # 长上下文
- OpenAI     # 通用能力
```

### 3.2 IM 平台接入

进入 **平台接入** 页面，配置各平台参数（详见第 7 节）。

### 3.3 配置文件

`~/.wanclaw/config.yaml`:

```yaml
gateway:
  port: 8000
  auth_enabled: true
  host: 0.0.0.0

ai:
  engine: deepseek
  deepseek:
    api_key: ${DEEPSEEK_API_KEY}
    model: deepseek-chat

platforms:
  wecom:
    enabled: true
    corp_id: your_corp_id
    agent_id: 1000001
    secret: ${WECOM_SECRET}

automation:
  screenshot_backend: mss      # mss / pyscreenshot / pil / pyautogui
  ocr_backend: tesseract      # tesseract / easyocr
  allowed_dirs:               # 允许操作的文件目录
    - /tmp/wanclaw
    - ~/Desktop
  app_whitelist:              # 允许启动的应用
    - chrome
    - edge
    - excel
    - notepad
```

---

## 4. 桌面助手（WebUI）

### 4.1 入口

登录管理后台后，点击左侧菜单 **桌面助手**，进入聊天界面。

### 4.2 使用方式

在输入框中输入自然语言指令，例如：

| 示例指令 | 说明 |
|---------|------|
| `帮我打开Chrome访问百度` | 启动浏览器并打开网页 |
| `截一张当前屏幕的截图` | 截取桌面截图 |
| `打开桌面上的文件夹` | 操作文件资源管理器 |
| `帮我把 C:/data 目录下的Excel文件合并` | 执行文件操作 |
| `监控一下CPU和内存使用率` | 系统信息查询 |
| `帮我打开 Excel 打开销售报表.xlsx` | 启动应用 |

### 4.3 执行流程

```
用户输入 → AI解析意图 → 任务拆解 → 权限校验 → 沙箱执行 → 结果反馈
```

执行过程会在界面中实时展示每一步骤的状态（等待/运行中/完成/失败）。

---

## 5. 桌面自动化

### 5.1 鼠标键盘控制

```python
from wanclaw.backend.automation import InputController, MouseButton

controller = InputController()
await controller.initialize()

# 鼠标操作
await controller.move_to(100, 200)           # 移动到坐标
await controller.click(x=100, y=200)          # 点击
await controller.double_click()                # 双击
await controller.right_click()                # 右键
await controller.scroll(3)                     # 滚动（正值向上，负值向下）

# 键盘操作
await controller.type_text("Hello WanClaw")   # 输入文本
await controller.press_key("enter")           # 按键
await controller.hotkey("ctrl", "c")          # 组合键
```

### 5.2 截图

```python
from wanclaw.backend.automation import Screenshot

screenshot = Screenshot()
await screenshot.initialize()

# 全屏截图
img = await screenshot.capture()

# 区域截图
region = Rectangle(x=0, y=0, width=800, height=600)
img = await screenshot.capture(region)

# 保存截图
await screenshot.save("/tmp/screen.png", region)
```

支持的截图后端（按速度优先级）：
1. **mss** — C 语言实现，最快（推荐）
2. **pyscreenshot** — 跨平台，纯 PIL
3. **PIL.ImageGrab** — Python 标准库
4. **pyautogui** — 最终回退

### 5.3 OCR 文字识别

```python
from wanclaw.backend.automation import VisionController

vision = VisionController()
await vision.initialize()

# 文字识别（返回所有识别结果）
results = await vision.recognize_text()
# [{'text': '提交', 'bbox': (100, 50, 150, 80), 'confidence': 0.95}]

# 定位文字坐标
point = await vision.locate_by_text("提交按钮")
if point:
    await controller.click(point.x, point.y)
```

OCR 后端（自动回退）：
1. **pytesseract** — 最高精度，需安装 Tesseract OCR 引擎
2. **EasyOCR** — 纯 Python，支持 80+ 语言，无需额外安装

### 5.4 模板匹配

```python
# 找图定位
point = await vision.locate_by_image("/tmp/button.png", confidence=0.8)
if point:
    await controller.click(point.x, point.y)

# 颜色定位
points = await vision.locate_by_color((255, 0, 0), tolerance=10)  # 找红色
```

### 5.5 智能等待

```python
# 等待文字出现（最长30秒）
point = await vision.wait_for_element("text", "登录", timeout=30)

# 等待图片出现
point = await vision.wait_for_element("image", "/tmp/ok_button.png", timeout=15)

# 等待并点击
await vision.click_element("text", "确认", controller, timeout=10)
```

---

## 6. 跨平台操作

### 6.1 窗口管理

```python
from wanclaw.backend.automation import get_window_manager

wm = get_window_manager()

# 列出所有窗口
windows = wm.enumerate_windows()
for w in windows:
    print(f"{w.title} - {w.process_name}")

# 获取当前激活窗口
active = wm.get_active_window()

# 窗口操作
wm.activate_window(hwnd)        # 激活窗口
wm.minimize_window(hwnd)        # 最小化
wm.maximize_window(hwnd)        # 最大化
wm.restore_window(hwnd)         # 还原
wm.close_window(hwnd)           # 关闭窗口
wm.hide_window(hwnd)            # 隐藏

# 按标题查找
win = wm.find_window_by_title("Chrome")

# 按进程名查找
chrome_windows = wm.find_window_by_process("chrome")
```

**平台支持**：

| 平台 | 实现 |
|------|------|
| Windows | pywin32 (Win32 API) |
| macOS | AppKit (NSWindow) |
| Linux | wnck (GTK) |

### 6.2 安全启动应用

```python
from wanclaw.backend.automation import get_app_launcher

launcher = get_app_launcher()

# 启动白名单应用
result = launcher.launch("chrome")
# {'success': True, 'app_name': 'Google Chrome', 'path': '/usr/bin/google-chrome'}

# 启动浏览器并打开URL
result = launcher.launch_url("https://www.baidu.com", browser="chrome")

# 查看可启动的应用
apps = launcher.list_allowed_apps()
# [{'id': 'chrome', 'name': 'Google Chrome', 'installed': True, ...}]

# 查看分类
browsers = launcher.list_allowed_apps(category="browser")
offices = launcher.list_allowed_apps(category="office")
```

**白名单软件列表**：

| 分类 | 应用 |
|------|------|
| 浏览器 | Chrome, Edge, Firefox, Brave |
| 办公 | Excel, Word, Outlook, WPS |
| 系统 | 记事本, 计算器, 文件资源管理器, 终端 |
| 媒体 | VLC |
| 开发 | VS Code, Sublime Text |

**跨平台 API 启动**：

| 平台 | API |
|------|-----|
| Windows | ShellExecuteW (Win32) |
| macOS | NSWorkspace |
| Linux | Gio / g_app_info_launch_default |

### 6.3 文件操作

```python
from wanclaw.backend.skills.office.file_manager import FileManagerSkill

fm = FileManagerSkill()

# 列出文件
result = await fm.execute({"action": "list", "path": "/tmp"})

# 复制
result = await fm.execute({
    "action": "copy",
    "source": "/tmp/a.txt",
    "destination": "/tmp/b.txt"
})

# 移动
result = await fm.execute({
    "action": "move",
    "source": "/tmp/a.txt",
    "destination": "/backup/a.txt"
})

# 删除
result = await fm.execute({"action": "delete", "path": "/tmp/temp.txt"})
```

### 6.4 系统信息

```python
from wanclaw.backend.skills.ops.process_monitor import ProcessMonitorSkill
from wanclaw.backend.skills.ops.health_checker import HealthCheckerSkill

pm = ProcessMonitorSkill()

# 列出进程
result = await pm.execute({"action": "list", "limit": 10})

# 终止进程
result = await pm.execute({"action": "kill", "pid": 1234})

# 系统健康检查
hc = HealthCheckerSkill()
result = await hc.execute({"action": "health_check"})
```

---

## 7. IM 平台接入

### 7.1 支持的平台

| 分类 | 平台 | 协议 |
|------|------|------|
| 企业通讯 | 企业微信 | 企业微信 API |
| | 飞书 | 飞书开放平台 |
| | 钉钉 | 钉钉开放平台 |
| 即时通讯 | Telegram | Bot API |
| | QQ | OneBot v11 |
| | 微信 | 企业微信/公众号 |
| | WhatsApp | WhatsApp Business API |
| | Discord | Discord Bot |
| | Slack | Slack API |
| 电商 | 淘宝/天猫 | 阿里百川 |
| | 京东 | 京东开放平台 |
| | 拼多多 | 拼多多开放平台 |
| | 抖音电商 | 抖音开放平台 |

### 7.2 企业微信接入

1. 登录 [企业微信管理后台](https://work.weixin.qq.com/)
2. 进入 **应用管理** → 创建应用 → 获取 `AgentId`
3. 进入 **我的企业** → 获取 `CorpId`
4. 点击 **设置企业微信网页 → 应用功能 → 企业微信** → 获取 `Secret`
5. 配置可信 IP（服务器 IP）
6. 在 WanClaw 管理后台填写配置：

```yaml
platforms:
  wecom:
    enabled: true
    corp_id: "wwxxxxxxxxxxxxxx"
    agent_id: 1000001
    secret: "your_secret_here"
    token: "auto_generate"
    encoding_aes_key: "auto_generate"
```

### 7.3 飞书接入

1. 登录 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用 → 获取 `App ID` 和 `App Secret`
3. 配置权限（消息权限需要 `im:message`）
4. 配置事件订阅 URL: `https://your-domain.com/api/webhook/feishu`
5. 在 WanClaw 管理后台填写：

```yaml
platforms:
  feishu:
    enabled: true
    app_id: "cli_xxxxxxxxxxxx"
    app_secret: "your_app_secret"
```

### 7.4 钉钉接入

1. 登录 [钉钉开放平台](https://open.dingtalk.com/)
2. 创建应用 → 获取 `AppKey` 和 `AppSecret`
3. 配置消息订阅地址: `https://your-domain.com/api/webhook/dingtalk`
4. 开通机器人能力

```yaml
platforms:
  dingtalk:
    enabled: true
    app_key: "dingxxxxxxxxxxxx"
    app_secret: "your_app_secret"
```

### 7.5 Telegram 接入

1. 在 Telegram 中搜索 `@BotFather`
2. 发送 `/newbot` 创建机器人 → 获取 `Bot Token`
3. 配置 Webhook: `https://your-domain.com/api/webhook/telegram`

```yaml
platforms:
  telegram:
    enabled: true
    bot_token: "123456789:ABCdefGHIjklMNOpqrSTUvwxyz"
```

### 7.6 QQ 接入（OneBot）

1. 安装 [NapCat](https://github.com/NapNeko/NapCatQQ) 或 [LLOneBot](https://github.com/LLOneBot/LLOneBot)
2. 配置正向 WebSocket: `ws://localhost:3001`
3. 获取 `access_token`

```yaml
platforms:
  qq:
    enabled: true
    host: "127.0.0.1"
    port: 3001
    access_token: "your_token"
```

---

## 8. AI 引擎配置

### 8.1 DeepSeek（推荐）

```yaml
ai:
  engine: deepseek
  deepseek:
    api_key: ${DEEPSEEK_API_KEY}
    model: deepseek-chat
    base_url: "https://api.deepseek.com"
```

### 8.2 Ollama（本地部署）

```bash
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | bash

# 下载模型
ollama pull qwen2.5
ollama pull llama3

# 启动服务
ollama serve
```

```yaml
ai:
  engine: ollama
  ollama:
    base_url: "http://localhost:11434"
    model: qwen2.5
```

### 8.3 通义千问

```yaml
ai:
  engine: dashscope
  dashscope:
    api_key: ${DASHSCOPE_API_KEY}
    model: qwen-plus
```

### 8.4 多模型自动容灾

WanClaw 支持配置多个 AI 提供商，当主模型不可用时自动切换：

```yaml
ai:
  engine: router
  router:
    strategy: failover    # failover / loadbalance
    providers:
      - name: deepseek
        priority: 1
        api_key: ${DEEPSEEK_API_KEY}
      - name: ollama
        priority: 2
        base_url: "http://localhost:11434"
      - name: dashscope
        priority: 3
        api_key: ${DASHSCOPE_API_KEY}
```

---

## 9. 技能系统

### 9.1 内置技能列表

#### 办公自动化

| 技能 | 功能 |
|------|------|
| ExcelProcessor | 合并/拆分/去重/筛选/排序/汇总/报告 |
| PDFProcessor | 合并/拆分/水印/加密/解密/文本提取 |
| WordProcessor | 创建/读取/替换/表格 |
| FileManager | 文件列表/复制/移动/删除/信息查看 |
| EmailProcessor | 发送/接收/搜索邮件 |
| SpreadsheetHandler | 表格读写 |

#### 运维管理

| 技能 | 功能 |
|------|------|
| ProcessMonitor | 进程列表/终止/暂停/恢复 |
| LogViewer | 日志查看/搜索/分析 |
| Backup | 文件备份/恢复 |
| HealthChecker | CPU/内存/磁盘监控 |
| LogCleaner | 日志清理 |

#### AI 增强

| 技能 | 功能 |
|------|------|
| OCRProcessor | 文字识别/名片/收据/文档 |
| NLPTaskGenerator | 自然语言任务生成 |

### 9.2 执行技能

#### 通过 API

```bash
curl -X POST http://localhost:8000/api/admin/skills/execute \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "skill_name": "excel_processor",
    "params": {
      "action": "merge",
      "file_paths": ["/data/sales1.xlsx", "/data/sales2.xlsx"],
      "output_path": "/data/merged.xlsx"
    }
  }'
```

#### 通过 WebUI

在 **技能与插件** 页面点击技能卡片，可直接执行。

#### 通过自然语言

在 **桌面助手** 输入：`帮我把 /data 下的所有 Excel 文件合并`

### 9.3 技能市场（ClawHub）

```bash
# 搜索技能
GET /api/clawhub/skills?query=excel&category=office

# 安装技能
POST /api/clawhub/install
{"name": "excel-advanced-formula"}

# 更新技能
POST /api/clawhub/update
{"name": "excel-advanced-formula"}
```

### 9.4 自定义技能开发

在 `wanclaw/backend/skills/custom/` 下创建技能：

```python
from wanclaw.backend.skills import BaseSkill, SkillResult, SkillCategory

class MyCustomSkill(BaseSkill):
    def __init__(self):
        super().__init__()
        self.name = "MyCustomSkill"
        self.description = "自定义技能描述"
        self.category = SkillCategory.OFFICE
        self.level = SkillLevel.BEGINNER
    
    async def execute(self, params):
        # 业务逻辑
        return SkillResult(
            success=True,
            message="执行成功",
            data={"result": "data"}
        )
```

注册技能需要添加 manifest：

```json
{
  "name": "my-custom-skill",
  "version": "1.0.0",
  "permissions": ["network", "filesystem:read"],
  "entry": "main.py"
}
```

---

## 10. 向量记忆

基于 LanceDB 的语义记忆系统，为 AI Agent 提供持久化记忆存储与检索。

### 10.1 概述

| 功能 | 说明 |
|------|------|
| 添加记忆 | 自动向量嵌入，支持分类标签和重要性评分 |
| 语义搜索 | 自然语言描述查找相关记忆 |
| 会话管理 | 按 session_id 分组管理记忆链 |
| 版本追踪 | 更新自动生成新版本，保留父版本 ID |
| 相似推荐 | 查找与当前记忆相似的其他记忆 |
| 过期清理 | 自动清理 N 天前的记忆 |

### 10.2 记忆类型

| 类型 | 说明 |
|------|------|
| `conversation` | 对话记录 |
| `fact` | 事实知识 |
| `preference` | 用户偏好 |
| `workflow` | 工作流记忆 |
| `context` | 上下文片段 |
| `document` | 文档摘要 |

### 10.3 API 使用

```bash
# 添加记忆
curl -X POST http://localhost:8000/api/admin/skills/execute \
  -H "Authorization: Bearer <token>" \
  -d '{
    "skill_name": "LanceDBMemory",
    "params": {
      "action": "add",
      "content": "用户偏好喝美式咖啡，不加糖",
      "session_id": "user_123",
      "memory_type": "preference",
      "tags": ["咖啡", "口味偏好"],
      "importance": 0.8
    }
  }'

# 语义搜索
curl -X POST http://localhost:8000/api/admin/skills/execute \
  -H "Authorization: Bearer <token>" \
  -d '{
    "skill_name": "LanceDBMemory",
    "params": {
      "action": "search",
      "query": "用户喜欢什么口味的咖啡",
      "session_id": "user_123",
      "limit": 5
    }
  }'
```

### 10.4 全部操作

| 操作 | 说明 |
|------|------|
| `add` | 添加记忆条目 |
| `search` | 语义搜索 |
| `get` | 获取单条记忆详情 |
| `update` | 更新记忆（保留版本链） |
| `delete` | 删除记忆 |
| `list` | 列出记忆 |
| `session_history` | 获取会话记忆链 |
| `similar` | 查找相似记忆 |
| `cleanup` | 清理过期记忆 |
| `stats` | 记忆统计 |

### 10.5 嵌入模型

优先使用 Ollama 嵌入模型：

```bash
export OLLAMA_BASE_URL=http://localhost:11434
ollama pull nomic-embed-text   # 推荐，中英文支持好
```

未配置时自动回退：HuggingFace Transformers → SHA256 哈希向量。

---

## 11. 浏览器 RPA

### 10.1 Playwright（主引擎）

```python
from wanclaw.backend.rpa import get_rpa_manager, BrowserConfig, BrowserType

rpa = await get_rpa_manager()

config = BrowserConfig(
    browser_type=BrowserType.CHROMIUM,
    headless=False,
    viewport={"width": 1920, "height": 1080}
)

async with rpa.new_browser(config) as browser:
    await browser.goto("https://www.baidu.com")
    await browser.fill(locator_by_placeholder("kw"), "WanClaw")
    await browser.click(locator_by_text("百度一下"))
    await browser.screenshot(path="/tmp/result.png")
```

### 10.2 Selenium（备用引擎）

```python
from wanclaw.backend.rpa import SeleniumDriver, SeleniumBrowser, SeleniumConfig

config = SeleniumConfig(
    browser=SeleniumBrowser.CHROME,
    headless=False
)

driver = SeleniumDriver(config)
await driver.initialize()

await driver.goto("https://www.baidu.com")
await driver.fill("css", "input[name='wd']", "WanClaw")
await driver.click("text", "百度一下")
await driver.screenshot(path="/tmp/result.png")

await driver.close()
```

### 10.3 元素定位方式

| 方式 | 示例 |
|------|------|
| ID | `locate_by_id("username")` |
| CSS | `locate_by_css(".btn-primary")` |
| XPath | `locate_by_xpath("//button[@type='submit']")` |
| 文本 | `locate_by_text("登录")` |
| 占位符 | `locate_by_placeholder("请输入密码")` |

---

## 12. 安全机制

### 12.1 沙箱隔离

- **危险模块拦截**：os、subprocess、shutil、socket 等被禁止导入
- **危险函数阻断**：exec、eval、compile、open 等被拦截
- **路径访问限制**：仅允许操作指定目录
- **AST 代码分析**：所有插件代码经过语法树分析

```python
# 沙箱检查项
BLOCKED_IMPORTS = ['os', 'subprocess', 'shutil', 'socket', ...]
BLOCKED_PATTERNS = ['rm -rf', 'eval(', '__import__(', ...]
ALLOWED_PATHS = ['/tmp/wanclaw', '~/Desktop']
```

### 12.2 权限声明

插件必须声明权限清单：

```json
{
  "permissions": ["network", "filesystem:read", "email"]
}
```

### 12.3 高危命令拦截

| 命令 | 状态 |
|------|------|
| `rm -rf /` | ✅ 拦截 |
| `sudo rm -rf` | ✅ 拦截 |
| `format` | ✅ 拦截 |
| `dd if=` | ✅ 拦截 |
| `mkfs` | ✅ 拦截 |

### 12.4 Prompt 注入检测

SoulScan 规则引擎（58+ 规则），检测以下攻击：

- 角色扮演逃逸（扮演管理员）
- 指令注入（忽略之前的指令）
- 编码绕过（Base64、URL 编码）
- 上下文注入

### 12.5 操作审计

所有操作均记录到审计日志：

```python
# 审计动作类型
USER_LOGIN, USER_LOGOUT, SKILL_EXECUTE, WORKFLOW_EXECUTE,
MESSAGE_SEND, CONFIG_UPDATE, FILE_OPERATION, PROCESS_KILL, ...
```

日志持久化到 Redis，支持查询和合规报表生成（GDPR、安全报表）。

---

## 13. API 参考

### 13.1 认证

```bash
# 登录获取 token
curl -X POST http://localhost:8000/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"password": "wanclaw"}'
# 响应: {"token": "Bearer eyJhbGci..."}
```

### 13.2 自然语言任务

```bash
curl -X POST http://localhost:8000/api/admin/ai/nl-task \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"command": "帮我打开Chrome访问百度"}'
```

### 13.3 技能执行

```bash
curl -X POST http://localhost:8000/api/admin/skills/execute \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"skill_name": "excel_processor", "params": {"action": "merge", "file_paths": []}}'
```

### 13.4 插件管理

```bash
GET  /api/plugins                    # 列表
POST /api/plugins/{name}/load        # 加载
POST /api/plugins/{name}/reload      # 重载（热加载）
POST /api/plugins/{name}/enable      # 启用
POST /api/plugins/{name}/disable     # 禁用
```

### 13.5 WebSocket 实时通信

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/messages");
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

---

## 14. 运维管理

### 14.1 服务管理

```bash
# systemd
systemctl start wanclaw       # 启动
systemctl stop wanclaw        # 停止
systemctl restart wanclaw     # 重启
systemctl status wanclaw      # 状态
systemctl enable wanclaw      # 开机自启

# 查看日志
journalctl -u wanclaw -f
```

### 14.2 健康检查

```bash
# 手动检查
curl http://localhost:8000/health

# 自动检查（配 cron）
*/1 * * * * /root/wanclaw/wanclaw-healthcheck.sh

# 异常自动重启
*/5 * * * * /root/wanclaw/wanclaw-healthcheck.sh --auto-restart
```

### 14.3 数据备份

```bash
# 通过 API 执行备份
curl -X POST http://localhost:8000/api/admin/skills/execute \
  -H "Authorization: Bearer <token>" \
  -d '{"skill_name": "backup", "params": {"action": "create"}}'
```

### 14.4 日志分析

```bash
# 查看最近操作日志
curl http://localhost:8000/api/admin/logs?limit=50

# 查看特定用户日志
curl http://localhost:8000/api/admin/logs?user_id=admin

# 查看审计日志
curl http://localhost:8000/api/admin/audit?action=SKILL_EXECUTE
```

---

## 15. 故障排查

### 15.1 常见问题

| 问题 | 解决方案 |
|------|---------|
| 启动失败 | 检查端口 8000 是否被占用：`lsof -i :8000` |
| AI 无响应 | 检查 API Key 是否配置正确 |
| 截图黑屏 | 安装 mss：`pip install mss` |
| OCR 识别失败 | 安装 Tesseract：`apt install tesseract-ocr`（Linux）|
| 企微消息不收 | 检查公网 IP 和防火墙，配置可信 IP |
| 飞书 Webhook 失败 | 确认事件订阅 URL 可公网访问 |
| 技能执行报错 | 查看 `journalctl -u wanclaw` 日志 |

### 15.2 日志位置

| 部署方式 | 日志位置 |
|---------|---------|
| systemd | `journalctl -u wanclaw` |
| 直接运行 | `stdout`（控制台输出） |
| Docker | `docker-compose logs wanclaw` |

### 15.3 调试模式

```bash
# 开启 debug 日志
export WANCLAW_LOG_LEVEL=DEBUG
python -m wanclaw.main
```

---

## 附录

### A. 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 是 |
| `WECOM_SECRET` | 企业微信 Secret | 平台启用时 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | 平台启用时 |
| `FEISHU_SECRET` | 飞书 App Secret | 平台启用时 |
| `OLLAMA_BASE_URL` | Ollama 地址 | 使用本地模型时 |
| `SECRET_KEY` | 会话加密密钥 | 推荐 |
| `WANCLAW_REDIS_URL` | Redis 连接地址 | 分布式部署时 |
| `WANCLAW_LOG_LEVEL` | 日志级别 (DEBUG/INFO/WARNING) | 可选 |

### B. 端口说明

| 端口 | 说明 |
|------|------|
| 8000 | WanClaw Gateway 主端口 |
| 6379 | Redis（可选） |
| 3306 | MySQL（可选） |

### C. 依赖清单

```
# 核心框架
fastapi, uvicorn, pydantic, pyyaml, httpx, websockets

# 桌面自动化（无 subprocess）
pyautogui, opencv-python, pytesseract, mss, pyscreenshot
easyocr, playwright, selenium

# 办公文档
openpyxl, python-docx, pypdf, pdfplumber, Pillow

# 系统信息
psutil

# 跨平台窗口管理
pywin32 (Windows), AppKit (macOS), wnck (Linux)

# AI
langchain, langchain-core

# 消息通道
python-telegram-bot

# 存储
redis, aiofiles, structlog
```

---

**版权所有 © 2025-2026 厦门亦梓科技有限公司 / 厦门万跃科技有限公司**  
**Copyright © 2025-2026 Xiamen Yizi Technology Co., Ltd. / Xiamen Wanyue Technology Co., Ltd. All Rights Reserved.**
