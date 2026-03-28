# WanClaw 多平台部署指南

## 目录
- [Windows 部署](#windows-部署)
- [Linux 部署](#linux-部署)
- [macOS 部署](#macos-部署)
- [Docker 部署](#docker-部署)
- [生产环境配置](#生产环境配置)
- [系统服务配置](#系统服务配置)
- [反向代理配置](#反向代理配置)

---

## 环境要求

| 项目 | 最低要求 | 推荐配置 |
|------|---------|---------|
| CPU | 1核 | 2核+ |
| 内存 | 512MB | 2GB+ |
| 磁盘 | 2GB | 10GB+ |
| Python | 3.9+ | 3.10/3.11 |
| 网络 | 能访问目标IM平台 | 固定IP |

---

## Windows 部署

### 方式一：直接运行（开发环境）

#### 1. 安装 Python

下载 Python 3.10+：[https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/)

安装时勾选 **Add Python to PATH**。

验证安装：
```powershell
python --version
pip --version
```

#### 2. 克隆项目

```powershell
git clone <repository_url>
cd wanclaw
```

#### 3. 创建虚拟环境

```powershell
python -m venv venv
.\venv\Scripts\activate
```

#### 4. 安装依赖

```powershell
pip install --upgrade pip
pip install pydantic pyyaml fastapi uvicorn httpx websockets python-telegram-bot aiofiles structlog psutil
```

#### 5. 配置

编辑 `config/config.yaml`：
```yaml
wecom:
  enabled: true
  corp_id: "YOUR_CORP_ID"
  agent_id: "YOUR_AGENT_ID"
  secret: "YOUR_SECRET"

feishu:
  enabled: false
  app_id: "YOUR_APP_ID"
  app_secret: "YOUR_APP_SECRET"
```

#### 6. 启动

```powershell
# 方式A：直接运行
python -m wanclaw.backend.im_adapter.api

# 方式B：使用uvicorn
uvicorn wanclaw.backend.im_adapter.api:app --host 0.0.0.0 --port 8000 --reload

# 方式C：后台运行
Start-Process -FilePath "uvicorn" -ArgumentList "wanclaw.backend.im_adapter.api:app --host 0.0.0.0 --port 8000" -WindowStyle Hidden
```

访问后台：`http://localhost:8000/admin`
默认密码：`wanclaw`

---

### 方式二：Windows 服务（NSSM）

#### 1. 下载 NSSM

下载地址：https://nssm.cc/download

将 `nssm.exe` 放到项目目录或系统 PATH 中。

#### 2. 创建服务

```powershell
nssm install WanClaw "C:\Python\python.exe"
nssm set WanClaw AppParameters "-m uvicorn wanclaw.backend.im_adapter.api:app --host 0.0.0.0 --port 8000"
nssm set WanClaw AppDirectory "C:\path\to\wanclaw"
nssm set WanClaw AppEnvironmentExtra "PYTHONPATH=C:\path\to\wanclaw"
nssm set WanClaw DisplayName "WanClaw IM Adapter"
nssm set WanClaw Description "WanClaw 多平台IM适配器服务"
nssm set WanClaw Start SERVICE_AUTO_START
```

#### 3. 管理服务

```powershell
# 启动
nssm start WanClaw

# 停止
nssm stop WanClaw

# 重启
nssm restart WanClaw

# 查看状态
nssm status WanClaw

# 查看日志
nssm console WanClaw
```

---

### 方式三：Windows 计划任务

创建启动脚本 `start.bat`：
```batch
@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
uvicorn wanclaw.backend.im_adapter.api:app --host 0.0.0.0 --port 8000
```

创建计划任务（每天早上8点自动启动）：
```powershell
schtasks /create /tn "WanClaw" /tr "\"C:\path\to\start.bat\"" /sc daily /st 08:00 /f
schtasks /run /tn "WanClaw"
```

---

### Windows 防火墙

允许 Python/uvicorn 通过防火墙：
```powershell
netsh advfirewall firewall add rule name="WanClaw" dir=in action=allow program="C:\Python\python.exe" enable=yes
netsh advfirewall firewall add rule name="WanClaw Port" dir=in action=allow protocol=tcp localport=8000
```

---

## Linux 部署

### 方式一：直接运行

#### 1. 系统准备

```bash
# Ubuntu/Debian
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git curl

# CentOS/RHEL
sudo yum update -y
sudo yum install -y python3 python3-pip git curl

# Arch Linux
sudo pacman -Syu python python-pip git curl
```

#### 2. 创建用户（生产环境建议）

```bash
sudo useradd -r -s /bin/false wanclaw 2>/dev/null || true
sudo mkdir -p /opt/wanclaw
sudo cp -r /path/to/wanclaw /opt/
sudo chown -R wanclaw:wanclaw /opt/wanclaw
```

#### 3. 虚拟环境

```bash
cd /opt/wanclaw
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install pydantic pyyaml fastapi uvicorn httpx websockets python-telegram-bot aiofiles structlog psutil
```

#### 4. 配置

```bash
sudo -u wanclaw nano /opt/wanclaw/config/config.yaml
```

#### 5. 启动测试

```bash
source venv/bin/activate
uvicorn wanclaw.backend.im_adapter.api:app --host 0.0.0.0 --port 8000
```

后台运行：
```bash
nohup uvicorn wanclaw.backend.im_adapter.api:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
echo $! > api.pid
```

---

### 方式二：systemd 服务（推荐）

创建服务文件：
```bash
sudo nano /etc/systemd/system/wanclaw.service
```

内容：
```ini
[Unit]
Description=WanClaw IM Adapter Service
After=network.target

[Service]
Type=simple
User=wanclaw
Group=wanclaw
WorkingDirectory=/opt/wanclaw
Environment="PATH=/opt/wanclaw/venv/bin"
ExecStart=/opt/wanclaw/venv/bin/uvicorn wanclaw.backend.im_adapter.api:app --host 0.0.0.0 --port 8000 --log-level info
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=append:/opt/wanclaw/logs/api.log
StandardError=append:/opt/wanclaw/logs/error.log

[Install]
WantedBy=multi-user.target
```

注册并启动：
```bash
sudo systemctl daemon-reload
sudo systemctl enable wanclaw
sudo systemctl start wanclaw
sudo systemctl status wanclaw
```

管理命令：
```bash
sudo systemctl start wanclaw    # 启动
sudo systemctl stop wanclaw     # 停止
sudo systemctl restart wanclaw   # 重启
sudo systemctl status wanclaw   # 状态
sudo journalctl -u wanclaw -f   # 实时日志
```

---

### 方式三：Supervisor 管理

```bash
sudo apt install -y supervisor
```

创建配置：
```bash
sudo nano /etc/supervisor/conf.d/wanclaw.conf
```

内容：
```ini
[program:wanclaw]
command=/opt/wanclaw/venv/bin/uvicorn wanclaw.backend.im_adapter.api:app --host 0.0.0.0 --port 8000
directory=/opt/wanclaw
user=wanclaw
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/opt/wanclaw/logs/supervisor.log
environment=PATH="/opt/wanclaw/venv/bin"
```

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start wanclaw
```

---

### 方式四：Docker 部署

#### Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "wanclaw.backend.im_adapter.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 构建并运行
```bash
docker build -t wanclaw .
docker run -d \
  --name wanclaw \
  -p 8000:8000 \
  -v /opt/wanclaw/config:/app/config \
  -v /opt/wanclaw/logs:/app/logs \
  --restart unless-stopped \
  wanclaw
```

docker-compose.yml：
```yaml
services:
  wanclaw:
    build: .
    container_name: wanclaw
    ports:
      - "8000:8000"
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
    environment:
      - PYTHONPATH=/app
    restart: unless-stopped
```

---

### 方式五：独立可执行文件（PyInstaller）

```bash
pip install pyinstaller
pyinstaller --onefile --name wanclaw \
  --add-data "config:config" \
  --hidden-import=pydantic \
  --hidden-import=fastapi \
  --hidden-import=uvicorn \
  --hidden-import=psutil \
  wanclaw.spec
```

---

## macOS 部署

### 方式一：直接运行

#### 1. 安装 Python

```bash
# 使用 Homebrew（推荐）
brew install python@3.11

# 或使用 pyenv
brew install pyenv
pyenv install 3.11.0
pyenv global 3.11.0
```

#### 2. 克隆并配置

```bash
git clone <repository_url>
cd wanclaw
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install pydantic pyyaml fastapi uvicorn httpx websockets python-telegram-bot aiofiles structlog psutil
```

#### 3. 启动

```bash
# 前台运行
uvicorn wanclaw.backend.im_adapter.api:app --host 0.0.0.0 --port 8000

# 后台运行
nohup uvicorn wanclaw.backend.im_adapter.api:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
echo $! > api.pid
```

---

### 方式二：LaunchD 服务

创建 plist 文件：
```bash
nano ~/Library/LaunchAgents/com.wanclaw.plist
```

内容：
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.wanclaw</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/username/wanclaw/venv/bin/uvicorn</string>
        <string>wanclaw.backend.im_adapter.api:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8000</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/username/wanclaw</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/Users/username/wanclaw/venv/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/username/wanclaw/logs/api.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/username/wanclaw/logs/error.log</string>
</dict>
</plist>
```

加载服务：
```bash
launchctl load ~/Library/LaunchAgents/com.wanclaw.plist
launchctl start com.wanclaw
launchctl list | grep wanclaw
```

---

### 方式三：Homebrew 服务

创建配方 `wanclaw.rb`：
```ruby
class Wanclaw < Formula
  desc "WanClaw IM Adapter"
  homepage "https://github.com/example/wanclaw"
  url "https://github.com/example/wanclaw/archive/v1.0.0.tar.gz"
  sha256 "..."
  depends_on "python@3.11"

  def install
    libexec.install Dir["*"]
    bin.install_symlink "#{libexec}/venv/bin/uvicorn" => "wanclaw"
  end

  plist_options manual: "wanclaw"

  def plist
    <<~EOS
      <?xml version="1.0" encoding="UTF-8"?>
      <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
      <plist version="1.0">
      <dict>
        <key>Label</key>
        <string>com.homebrew.wanclaw</string>
        <key>ProgramArguments</key>
        <array>
          <string>#{opt_bin}/wanclaw</string>
          <string>wanclaw.backend.im_adapter.api:app</string>
          <string>--host</string>
          <string>0.0.0.0</string>
          <string>--port</string>
          <string>8000</string>
        </array>
        <key>RunAtLoad</key>
        <true/>
      </dict>
      </plist>
    EOS
  end
end
```

```bash
brew install wanclaw
brew services start wanclaw
```

---

## 生产环境配置

### 安全配置

#### 1. 修改默认密码

登录后台 → 安全设置 → 修改密码

或直接编辑配置：
```bash
# 生成密码哈希
python3 -c "import hashlib; print(hashlib.sha256('your_new_password + salt + wanclaw_salt_v1'.encode()).hexdigest())"
```

#### 2. 限制访问IP

```bash
# 仅允许内网访问
ufw allow from 192.168.0.0/16 to any port 8000
# 或使用nginx限制
```

#### 3. HTTPS 配置（见反向代理章节）

#### 4. 环境变量配置

```bash
export WANCLAW_CONFIG="/opt/wanclaw/config/config.yaml"
export WANCLAW_LOG_LEVEL="warning"
export WANCLAW_SECRET_KEY="your-secret-key-here"
```

### 性能配置

#### Gunicorn + Uvicorn Workers

```bash
pip install gunicorn
gunicorn wanclaw.backend.im_adapter.api:app \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  -b 0.0.0.0:8000 \
  --timeout 120 \
  --log-level info
```

#### Nginx 负载均衡

```nginx
upstream wanclaw_backend {
    least_conn;
    server 127.0.0.1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 weight=1 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/ssl/certs/wanclaw.crt;
    ssl_certificate_key /etc/ssl/private/wanclaw.key;

    location / {
        proxy_pass http://wanclaw_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    location /admin {
        proxy_pass http://wanclaw_backend;
        # 可添加 Basic Auth 双重认证
        auth_basic "WanClaw Admin";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 系统服务配置

### 日志轮转（logrotate）

```bash
sudo nano /etc/logrotate.d/wanclaw
```

内容：
```
/opt/wanclaw/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0644 wanclaw wanclaw
    postrotate
        systemctl reload wanclaw > /dev/null 2>&1 || true
    endscript
}
```

---

### 防火墙配置

#### Ubuntu (UFW)
```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # WanClaw
sudo ufw enable
sudo ufw status
```

#### CentOS (firewalld)
```bash
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports
```

#### macOS (pf)
```bash
sudo nano /etc/pf.anchors/wanclaw
# 内容：
# pass in proto tcp from any to any port 8000

sudo nano /etc/pf.conf
# 添加： load anchor="wanclaw" from "/etc/pf.anchors/wanclaw"

sudo pfctl -f /etc/pf.conf
sudo pfctl -e
```

---

### 备份策略

```bash
#!/bin/bash
# backup.sh - 每日备份脚本
DATE=$(date +%Y%m%d)
BACKUP_DIR=/opt/backups/wanclaw
mkdir -p $BACKUP_DIR

# 备份配置
tar -czf $BACKUP_DIR/config_$DATE.tar.gz /opt/wanclaw/config/

# 备份日志（可选）
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz /opt/wanclaw/logs/

# 保留30天
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "[$(date)] 备份完成: $BACKUP_DIR"
```

crontab：
```bash
crontab -e
# 每天凌晨3点备份
0 3 * * * /opt/wanclaw/scripts/backup.sh >> /var/log/backup.log 2>&1
```

---

## 反向代理配置

### Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        
        # WebSocket支持
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

### Caddy 反向代理（自动HTTPS）

```caddy
your-domain.com {
    reverse_proxy /ws/* {
        header_up Connection {>Connection}
        header_up Upgrade {>Upgrade}
    }

    reverse_proxy /* localhost:8000
}
```

---

## 快速启动命令汇总

| 平台 | 命令 |
|------|------|
| **Windows (开发)** | `uvicorn wanclaw.backend.im_adapter.api:app --host 0.0.0.0 --port 8000 --reload` |
| **Linux (systemd)** | `sudo systemctl start wanclaw` |
| **Linux (nohup)** | `nohup uvicorn wanclaw.backend.im_adapter.api:app --host 0.0.0.0 --port 8000 &` |
| **macOS (launchd)** | `launchctl start com.wanclaw` |
| **Docker** | `docker run -d -p 8000:8000 wanclaw` |
| **Docker Compose** | `docker compose up -d` |

## 验证部署

```bash
# 健康检查
curl http://localhost:8000/health

# 登录获取token
curl -X POST -H "Content-Type: application/json" \
  -d '{"password":"wanclaw"}' \
  http://localhost:8000/api/admin/login

# 查看技能数量
curl http://localhost:8000/api/admin/skills \
  -H "Authorization: YOUR_TOKEN"

# 查看系统信息
curl http://localhost:8000/api/admin/system \
  -H "Authorization: YOUR_TOKEN"

# 访问管理后台
open http://localhost:8000/admin
```
