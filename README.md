# TG Downloader Bot 🚀

基于 Telegram 的 NAS 下载机器人。将视频、音乐、图片、文档、磁力链转发到群中，自动下载到 NAS 本地存储。

## 功能特性

| 功能 | 说明 |
|------|------|
| 🎬 **视频下载** | mp4, mkv, avi, mov, webm, flv, wmv, ts 等 |
| 🎵 **音频下载** | mp3, flac, wav, aac, ogg, m4a, opus, wma 等 |
| 🖼️ **图片下载** | jpg, png, gif, webp, bmp, tiff, svg 等 |
| 📄 **文档下载** | pdf, zip, rar, 7z, tar, doc(x), xls(x), ppt(x), txt, epub 等 |
| 🧲 **磁力链/种子** | 集成 qBittorrent，自动下载 |
| 📊 **分类存储** | 按类型自动归档到不同目录 |
| 🔔 **完成通知** | 下载完成后群内 DM 通知 |
| 📈 **进度通知** | 大文件(>50MB) 每 25% 通知一次进度 |
| 🌐 **Web 管理** | FastAPI 管理界面，查看统计/文件/磁力链状态 |
| 🖼️ **表情贴纸** | sticker 自动归入图片分类 |

### 文件扩展名 ↔ 分类映射

| 分类 | 扩展名 |
|------|--------|
| **video** | `.mp4` `.mkv` `.avi` `.mov` `.webm` `.flv` `.wmv` `.ts` |
| **audio** | `.mp3` `.flac` `.wav` `.aac` `.ogg` `.m4a` `.opus` `.wma` |
| **photo** | `.jpg` `.jpeg` `.png` `.gif` `.webp` `.bmp` `.tiff` `.svg` |
| **document** | `.pdf` `.zip` `.rar` `.7z` `.tar` `.gz` `.doc` `.docx` `.xls` `.xlsx` `.ppt` `.pptx` `.txt` `.epub` `.cbz` |
| **torrent** | `.torrent` |

> 除扩展名外，系统还依据 MIME 类型（`video/*`、`audio/*`、`image/*`）进行分类。Telegram 的 `voice` 消息归入 audio，`sticker`（贴纸）归入 photo。

## 运行模式

本项目支持两种运行模式：

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| **User 模式** | 使用闲置的 Telegram 账号作为"机器人" | 个人使用，无文件大小限制，**推荐** ✅ |
| **Bot 模式** | 使用 Bot API + Telethon 混合 | 需要 `/command` 体验，**暂未实现** ⏳ |

> **当前已实现：User 模式**。Bot 模式入口已预留，尚未开发完成。

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Host (NAS)                      │
│                                                           │
│  ┌─────────────────────────┐     ┌──────────────────┐    │
│  │  TG Downloader           │     │  qBittorrent     │    │
│  │  (Telethon User Client)  │────▶│  (Web API v2)    │    │
│  │                          │     │                  │    │
│  │  监听群消息 → 下载        │     │  磁力链/种子下载  │    │
│  │  通知 → 群回复(DM)       │     │  进度监控 → 通知 │    │
│  └─────────────────────────┘     └──────────────────┘    │
│           │                        │                      │
│           ▼                        ▼                      │
│  ┌──────────────────────────────────────────────────┐    │
│  │               /downloads/ (共享存储)               │    │
│  │  ├── video/     ├── audio/     ├── photo/        │    │
│  │  ├── document/  └── torrents/  (qBittorrent)     │    │
│  │      └── watch/ (qBittorrent 监控目录)            │    │
│  └──────────────────────────────────────────────────┘    │
│                                                           │
│  ┌──────────────────┐                                    │
│  │  Web 管理界面     │  ← 也可独立访问                     │
│  │  FastAPI :8081   │                                    │
│  └──────────────────┘                                    │
└─────────────────────────────────────────────────────────┘
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

### 🚀 一键部署

```bash
# 只需 3 条命令：
git clone https://github.com/wenqa1/tg-downloader.git
cd tg-downloader
bash deploy.sh
```

> `deploy.sh` 会自动完成：检查环境 → 创建 `.env`（首次引导配置）→ 创建目录 → 构建镜像 → 启动服务。

### 安装步骤（手动）

#### 1. 下载项目

```bash
git clone https://github.com/wenqa1/tg-downloader.git
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
🔐 Enter the verification code: *****
```

输入验证码后，按 `Ctrl+P` 然后 `Ctrl+Q` 安全断开（不要用 `Ctrl+C`）。

> 会话会自动保存在 `core/sessions/` 目录，下次启动不需要再输入验证码。
>
> 如果账号启用了两步验证（2FA），还需要输入密码：
> ```
> 🔐 Enter your 2FA password:
> ```

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

启动成功后，你的主号会收到一条私聊通知：
```
🟢 TG Downloader 已启动
运行模式: user
群组 ID: -1001234567890
发送 help 查看可用命令
```

### 使用方式

将需要下载的内容转发到私密群中：

| 操作 | 效果 |
|------|------|
| 转发视频/音乐/图片 | 自动下载到 `/downloads/{分类}/` |
| 转发文档 | 自动下载到 `/downloads/document/` |
| 发送磁力链接 | 自动添加到 qBittorrent 下载 |
| 发送 `.torrent` 文件 | 自动添加到 qBittorrent 下载 |
| 发送 `.torrent` URL | 自动下载种子后提交到 qBittorrent |
| 发送贴纸 (sticker) | 自动下载为图片到 `/downloads/photo/` |

群内可用命令（支持 `help` 或 `/help` 两种格式）：

| 命令 | 说明 |
|------|------|
| `help` 或 `start` | 显示帮助信息 |
| `status` | 查看 qBittorrent 下载状态（按状态分组） |
| `stats` | 查看下载统计（各分类文件数、总大小、运行时间） |
| `id` | 获取当前群组 Chat ID 和你的 User ID |

#### 下载进度通知

大文件下载时，机器人会在 25%、50%、75% 时发送进度通知：
```
⏳ 下载中: `example_video.mp4`
📊 50% (256.0 MB)
```

磁力链和种子文件每 25% 汇报一次进度，下载完成后通知：
```
✅ 磁力链下载完成
📄 `Ubuntu 24.04 Desktop.iso`
```

## Web 管理界面

项目附带一个 Web 管理界面，可以通过浏览器查看下载统计、浏览文件、管理磁力链。

启动后自动运行在 `http://你的NASIP:8081`。

### 页面

| 页面 | 路径 | 功能 |
|------|------|------|
| 📊 **总览** | `/` | 统计卡片、分类占比、最近下载、系统状态 |
| 📁 **文件** | `/files` | 按分类浏览文件、搜索文件 |
| 🧲 **磁力链** | `/torrents` | qBittorrent 下载进度、状态、速度、ETA |
| ⚙️ **设置** | `/settings` | Web 界面管理 API 凭证、Telegram 配置（无需编辑 .env） |

> 总览页面每 15 秒自动刷新，磁力链页面每 10 秒自动刷新。

### API 接口

| 接口 | 说明 |
|------|------|
| `GET /api/stats` | 仪表盘统计数据（分类统计、最近事件、qB/Bot 状态） |
| `GET /api/files/{category}` | 列出某分类文件（支持 `?search=` 搜索） |
| `GET /api/torrents` | qBittorrent 下载列表（进度/速度/ETA/比率） |
| `GET /api/logs` | 最近下载事件（从日志解析） |
| `GET /api/settings` | 获取当前配置（合并 .env + settings.json） |
| `PUT /api/settings` | 保存配置到 settings.json（重启后生效） |

#### `/api/stats` 响应结构

```json
{
  "stats": {
    "categories": {
      "video": { "count": 12, "size": 1073741824, "size_str": "1.0 GB" },
      "audio": { "count": 5, "size": 52428800, "size_str": "50.0 MB" },
      "photo": { "count": 88, "size": 104857600, "size_str": "100.0 MB" },
      "document": { "count": 3, "size": 15728640, "size_str": "15.0 MB" },
      "torrents": { "count": 2, "size": 2097152, "size_str": "2.0 MB" }
    },
    "total_files": 110,
    "total_size": 1243612160,
    "total_size_str": "1.2 GB"
  },
  "recent": [
    { "time": "5分钟前", "type": "complete", "icon": "✅", "message": "下载完成..." }
  ],
  "qb_status": "online",
  "bot_status": "online"
}
```

#### `/api/torrents` 响应结构

```json
{
  "torrents": [
    {
      "name": "Ubuntu 24.04 Desktop.iso",
      "progress": 67.8,
      "state": "downloading",
      "size": "4.9 GB",
      "downloaded": "3.3 GB",
      "speed": "12.5 MB/s",
      "eta": "2m 15s",
      "ratio": 0.5
    }
  ],
  "count": 1
}
```

## 配置说明

### 环境变量

| 变量 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| `RUN_MODE` | 否 | `user` | 运行模式: `user` / `bot`（bot 暂未实现） |
| `TELEGRAM_API_ID` | **是** | — | 从 https://my.telegram.org 获取 |
| `TELEGRAM_API_HASH` | **是** | — | 从 https://my.telegram.org 获取 |
| `PHONE_NUMBER` | User 模式 | — | 副号手机号（Telethon 登录用） |
| `BOT_TOKEN` | Bot 模式 | — | Bot API Token（暂未实现） |
| `OWNER_USER_ID` | **是** | — | 你的主号 User ID（白名单 + 通知接收） |
| `TARGET_GROUP_CHAT_ID` | **是** | — | 监听的目标群 Chat ID |
| `DOWNLOAD_BASE_PATH` | 否 | `/downloads` | 下载根目录（容器内路径） |
| `QBITTORRENT_URL` | 否 | `http://qbittorrent:8080` | qBittorrent Web API 地址 |
| `QBITTORRENT_USERNAME` | 否 | `admin` | qBittorrent 登录用户名 |
| `QBITTORRENT_PASSWORD` | 否 | `adminadmin` | qBittorrent 登录密码 |
| `WEB_PORT` | 否 | `8081` | Web 管理界面端口 |
| `WEB_HOST` | 否 | `0.0.0.0` | Web 管理界面监听地址 |

> `WEB_PORT` 和 `WEB_HOST` 仅影响 web 服务容器，通过 `docker-compose.yml` 的 `environment` 字段传入。

### 下载目录结构

```
/downloads/
├── video/          # 视频文件 (.mp4, .mkv, .avi, .mov, .webm...)
├── audio/          # 音频/音乐文件 (.mp3, .flac, .wav, .aac...)
├── photo/          # 图片文件 (.jpg, .png, .gif, .webp...) 含 sticker
├── document/       # 文档/其他文件 (.pdf, .zip, .rar, .doc...)
└── torrents/       # 磁力链/种子下载
    └── watch/      # qBittorrent 监控目录（放入即自动下载）
```

> 文件重名时自动追加 `_1`、`_2` 后缀避免覆盖。

## 安全与权限

### 白名单机制

只有 `OWNER_USER_ID` 指定的用户发送的消息才会被处理。未授权用户发消息将被忽略，并通知主人：

```
⚠️ 未授权的用户 (ID: `12345678`) 尝试使用机器人
消息已忽略，如需授权请添加到 OWNER_USER_ID
```

### 消息隔离

- 只处理 `TARGET_GROUP_CHAT_ID` 指定群的消息
- 自动跳过机器人自己发送的消息（避免循环）

## 常见问题

### qBittorrent 无法连接？

1. 确保 qBittorrent 容器已启动：`docker-compose ps`
2. 检查 qBittorrent Web UI 是否可以访问：`http://你的NASIP:8080`
3. 确认 `.env` 中的用户名密码是否正确
4. 容器首次启动时 qBittorrent 可能较慢，等待 10-20 秒后自动重试

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
├── docker-compose.yml          # 容器编排（tg-downloader + web + qbittorrent）
├── .env.example                # 环境变量配置模板
├── .gitignore
├── README.md
├── core/                       # 核心服务
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── sessions/               # Telethon 会话文件（自动生成）
│   ├── logs/                   # 日志文件（自动轮转，10MB × 5 份）
│   └── src/
│       ├── main.py             # 主入口，模式分发
│       ├── config.py           # 配置加载（dataclass + dotenv）
│       ├── receivers/          # 消息接收层
│       │   ├── base.py         # BaseReceiver 抽象接口
│       │   └── user_receiver.py  # Telethon 用户模式接收器
│       ├── handlers/           # 消息处理层（按职责链式调用）
│       │   ├── file_handler.py   # 文件/媒体下载（含进度通知）
│       │   ├── magnet_handler.py # 磁力链/种子 URL 处理
│       │   └── command_handler.py# 文本命令处理
│       ├── downloaders/        # 下载引擎
│       │   └── qb_client.py    # qBittorrent Web API v2 客户端
│       ├── notifiers/          # 通知模块
│       │   ├── base.py         # BaseNotifier 抽象接口
│       │   └── user_notifier.py  # Telethon 用户模式通知
│       ├── organizer/          # 文件组织
│       │   └── classifier.py  # 文件分类 + 路径生成 + 重名处理
│       └── web/                # Web 管理界面（FastAPI + Jinja2）
│           ├── server.py       # FastAPI 服务 + API 路由
│           ├── templates/      # Jinja2 模板
│           │   ├── base.html       # 布局骨架（侧边栏 + 主题）
│           │   ├── dashboard.html  # 总览页
│           │   ├── files.html      # 文件浏览页
│           │   └── torrents.html   # 磁力链管理页
│           └── static/         # 静态资源
│               ├── style.css   # 暗色主题样式
│               └── app.js      # 共享 JavaScript
├── qbittorrent/                # qBittorrent 配置（自动生成）
│   └── config/
└── downloads/                  # 下载文件（宿主机持久化）
    ├── video/
    ├── audio/
    ├── photo/
    ├── document/
    └── torrents/
        └── watch/              # qBittorrent 自动监控目录
```

## 技术栈

| 组件 | 用途 | 版本 |
|------|------|------|
| **Python** | 运行环境 | 3.12 (slim) |
| **Telethon** | MTProto 客户端（无限文件下载） | ≥1.37 |
| **FastAPI + Uvicorn** | Web 管理界面 | ≥0.115 |
| **Jinja2** | HTML 模板引擎 | ≥3.1 |
| **aiohttp** | 异步 HTTP（qBittorrent Web API） | ≥3.9 |
| **python-dotenv** | 环境变量加载 | ≥1.0 |
| **qBittorrent** | 磁力链/种子下载器 | latest (linuxserver) |
| **Docker Compose** | 容器编排 | 3.8+ |

## 许可证

MIT
