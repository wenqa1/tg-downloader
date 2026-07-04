# TG Downloader Bot 🚀

基于 Telegram 的 NAS 下载机器人。将视频、音乐、图片、文档、磁力链转发到群中，自动下载到 NAS 本地存储。

## 功能特性

| 功能 | 说明 |
|------|------|
| 🎬 **视频下载** | mp4, mkv, avi, mov, webm 等 |
| 🎵 **音频下载** | mp3, flac, wav, aac, ogg 等 |
| 🖼️ **图片下载** | jpg, png, gif, webp 等 |
| 📄 **文档下载** | pdf, zip, rar, doc, txt 等 |
| 🧲 **磁力链/种子** | 集成 qBittorrent，自动下载 |
| 📊 **分类存储** | 按类型自动归档到不同目录 |
| 🔔 **完成通知** | 下载完成后群内通知 |

## 运行模式

本项目支持两种运行模式：

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| **User 模式** | 使用闲置的 Telegram 账号作为"机器人" | 个人使用，无文件大小限制，推荐 |
| **Bot 模式** | 使用 Bot API + Telethon 混合 | 需要 /command 体验，后续开发 |

> **当前已实现：User 模式**

## 架构

```
┌─────────────────────────────────────────────────────┐
│                    Docker Host (NAS)                  │
│                                                       │
│  ┌─────────────────────┐     ┌──────────────────┐    │
│  │  TG Downloader       │     │  qBittorrent     │    │
│  │  (Telethon Client)   │────▶│  (Web API)       │    │
│  │                      │     │                  │    │
│  │  监听群消息 → 下载    │     │  磁力链/种子下载  │    │
│  └─────────────────────┘     └──────────────────┘    │
│           │                        │                  │
│           ▼                        ▼                  │
│  ┌──────────────────────────────────────────────┐    │
│  │           /downloads/ (共享存储)              │    │
│  │  ├── video/    ├── audio/    ├── photo/     │    │
│  │  ├── document/ └── torrents/ (qBittorrent)  │    │
│  └──────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

## 快速开始

### 前置准备

1. **Telegram API 凭证**（必须）
   - 访问 https://my.telegram.org
   - 登录后进入 "API Development Tools"
   - 创建一个应用，获取 **API ID** 和 **API Hash**

2. **闲置的 Telegram 账号**
   - 准备一个不常用的手机号，用于 Telethon 登录

3. **Docker 环境**
   - NAS 需安装 Docker 和 Docker Compose

4. **私密群组**
   - 在 Telegram 中创建一个私密群组
   - 把你的主号 + 闲置副号都拉进群

### 安装步骤

#### 1. 下载项目

```bash
git clone <your-repo-url> tg-downloader
cd tg-downloader
```

#### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件填入你的配置
```

#### 3. 配置 `.env` 文件

```ini
# 运行模式
RUN_MODE=user

# Telegram API 凭证（必填）
TELEGRAM_API_ID=12345
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890

# 闲置副号的手机号（User 模式必填）
PHONE_NUMBER=+8613800138000

# 你的主号 Telegram User ID
OWNER_USER_ID=123456789

# 私密群的 Chat ID（初始可留空，首次运行会列出所有对话）
TARGET_GROUP_CHAT_ID=-1001234567890

# qBittorrent 配置
QBITTORRENT_URL=http://qbittorrent:8080
QBITTORRENT_USERNAME=admin
QBITTORRENT_PASSWORD=adminadmin
```

#### 4. 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看日志（首次运行需要输入验证码）
docker logs tg-downloader -f
```

#### 5. 首次登录（验证码）

第一次运行需要输入 Telegram 的登录验证码：

```bash
# 附加到容器交互终端
docker attach tg-downloader
```

会看到类似提示：
```
Please enter the code you received: *****
```

输入验证码后，按 `Ctrl+P` 然后 `Ctrl+Q` 安全断开（不要用 `Ctrl+C`）。

> 会话会自动保存在 `core/sessions/` 目录，下次启动不需要再输入验证码。

> 如果账号启用了两步验证，还需要输入密码。

#### 6. 获取群组 Chat ID

首次启动时，如果未配置 `TARGET_GROUP_CHAT_ID`，日志会输出所有可用的对话列表：

```
WARNING  Available chats:
  • 我的群: ID = -1001234567890 (Type: Channel)
  • 好友小群: ID = -1009876543210 (Type: Channel)
```

找到你的私密群 ID，填入 `.env` 文件，然后重启：

```bash
docker-compose restart tg-downloader
```

### 使用方式

将需要下载的内容转发到私密群中：

| 操作 | 效果 |
|------|------|
| 转发视频/音乐/图片 | 自动下载到 `/downloads/{分类}/` |
| 转发文档 | 自动下载到 `/downloads/document/` |
| 发送磁力链接 | 自动添加到 qBittorrent 下载 |
| 发送 `.torrent` 文件 | 自动添加到 qBittorrent 下载 |

群内可用命令：

| 命令 | 说明 |
|------|------|
| `help` 或 `start` | 显示帮助信息 |
| `status` | 查看 qBittorrent 下载状态 |
| `stats` | 查看下载统计 |
| `id` | 获取群组和用户 ID |

## Web 管理界面

项目附带一个 Web 管理界面，可以通过浏览器查看下载统计、浏览文件、管理磁力链。

启动后会自动运行在 `http://你的NASIP:8081`。

### 页面

| 页面 | 路径 | 功能 |
|------|------|------|
| 📊 **总览** | `/` | 统计卡片、分类占比、最近下载、系统状态 |
| 📁 **文件** | `/files` | 按分类浏览文件、搜索 |
| 🧲 **磁力链** | `/torrents` | qBittorrent 下载进度、状态 |

### API 接口

| 接口 | 说明 |
|------|------|
| `GET /api/stats` | 仪表盘统计数据 |
| `GET /api/files/{category}` | 列出某分类文件（支持 `?search=` 搜索） |
| `GET /api/torrents` | qBittorrent 下载列表 |
| `GET /api/logs` | 最近下载事件 |

## 配置说明

### 环境变量

| 变量 | 必需 | 说明 |
|------|------|------|
| `RUN_MODE` | 否 | 运行模式: `user` / `bot`（默认 `user`） |
| `TELEGRAM_API_ID` | 是 | 从 my.telegram.org 获取 |
| `TELEGRAM_API_HASH` | 是 | 从 my.telegram.org 获取 |
| `PHONE_NUMBER` | User 模式 | 副号手机号 |
| `BOT_TOKEN` | Bot 模式 | Bot API Token（暂未实现） |
| `OWNER_USER_ID` | 是 | 你的主号 User ID（白名单 + 通知） |
| `TARGET_GROUP_CHAT_ID` | 是 | 监听的群 ID |
| `DOWNLOAD_BASE_PATH` | 否 | 下载根目录（默认 `/downloads`） |
| `QBITTORRENT_URL` | 否 | qBittorrent Web API 地址 |
| `QBITTORRENT_USERNAME` | 否 | qBittorrent 用户名 |
| `QBITTORRENT_PASSWORD` | 否 | qBittorrent 密码 |

### 下载目录结构

```
/downloads/
├── video/          # 视频文件
├── audio/          # 音频/音乐文件
├── photo/          # 图片文件
├── document/       # 文档/其他文件
└── torrents/       # 磁力链/种子下载
    └── watch/      # qBittorrent 监控目录
```

## 常见问题

### qBittorrent 无法连接？

1. 确保 qBittorrent 容器已启动：`docker-compose ps`
2. 检查 qBittorrent Web UI 是否可以访问：`http://你的NASIP:8080`
3. 确认 `.env` 中的用户名密码是否正确

### 验证码过期？

Telethon 会话文件保存在 `core/sessions/` 目录。如果登录过期：

```bash
docker-compose down
rm -rf core/sessions/*
docker-compose up -d
docker attach tg-downloader
```

### 如何升级？

```bash
cd tg-downloader
git pull
docker-compose down
docker-compose up -d --build
```

## 目录结构

```
tg-downloader/
├── docker-compose.yml          # 容器编排
├── .env.example                # 配置模板
├── .gitignore
├── README.md
├── core/                       # 核心服务
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── sessions/               # Telethon 会话（自动生成）
│   ├── logs/                   # 日志文件
│   └── src/
│       ├── main.py             # 主入口
│       ├── config.py           # 配置加载
│       ├── receivers/          # 消息接收
│       │   ├── base.py
│       │   └── user_receiver.py
│       ├── handlers/           # 消息处理
│       │   ├── file_handler.py
│       │   ├── magnet_handler.py
│       │   └── command_handler.py
│       ├── downloaders/        # 下载引擎
│       │   └── qb_client.py
│       ├── notifiers/          # 通知模块
│       │   ├── base.py
│       │   └── user_notifier.py
│       ├── organizer/          # 文件分类
│       │   └── classifier.py
│       └── web/                # Web 管理界面
│           ├── server.py       # FastAPI 服务
│           ├── templates/      # HTML 模板
│           │   ├── base.html
│           │   ├── dashboard.html
│           │   ├── files.html
│           │   └── torrents.html
│           └── static/         # CSS/JS
│               ├── style.css
│               └── app.js
├── qbittorrent/                # qBittorrent 配置（自动生成）
│   └── config/
└── downloads/                  # 下载文件
    ├── video/
    ├── audio/
    ├── photo/
    ├── document/
    └── torrents/
```

## 技术栈

- **Python 3.12** - 运行环境
- **Telethon** - MTProto 客户端（无限文件下载）
- **FastAPI + Uvicorn** - Web 管理界面
- **aiohttp** - 异步 HTTP（qBittorrent API）
- **python-dotenv** - 配置加载
- **qBittorrent** - 磁力链/种子下载器

## 许可证

MIT
