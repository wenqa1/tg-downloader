# TG Downloader Bot 🚀

基于 Telegram 的 NAS 下载机器人。将视频、音乐、图片、文档、磁力链转发到群中，自动下载到 NAS 本地存储。

单容器运行，通过 Web 界面完成所有配置，无需编辑配置文件。

```bash
# 🚀 一键部署
git clone https://github.com/wenqa1/tg-downloader.git
cd tg-downloader && bash deploy.sh
```

## 功能特性

| 功能 | 说明 |
|------|------|
| 🎬 **视频下载** | mp4, mkv, avi, mov, webm, flv, wmv, ts 等 |
| 🎵 **音频下载** | mp3, flac, wav, aac, ogg, m4a, opus, wma 等 |
| 🖼️ **图片下载** | jpg, png, gif, webp, bmp, tiff, svg 等 |
| 📄 **文档下载** | pdf, zip, rar, 7z, tar, doc(x), xls(x), ppt(x), txt, epub 等 |
| 🧲 **磁力链/种子** | 集成外部 qBittorrent，自动下载 |
| 📊 **分类存储** | 按类型自动归档到不同目录 |
| 🔔 **完成通知** | 下载完成后 DM 通知 |
| 📈 **进度通知** | 大文件(>50MB) 每 25% 通知一次进度 |
| 🌐 **Web 管理** | 单容器自带管理界面，查看统计/文件/磁力链/配置 |
| 🖼️ **贴纸处理** | sticker 自动归入图片分类 |

### 文件扩展名 ↔ 分类映射

| 分类 | 扩展名 |
|------|--------|
| **video** | `.mp4` `.mkv` `.avi` `.mov` `.webm` `.flv` `.wmv` `.ts` |
| **audio** | `.mp3` `.flac` `.wav` `.aac` `.ogg` `.m4a` `.opus` `.wma` |
| **photo** | `.jpg` `.jpeg` `.png` `.gif` `.webp` `.bmp` `.tiff` `.svg` |
| **document** | `.pdf` `.zip` `.rar` `.7z` `.tar` `.gz` `.doc` `.docx` `.xls` `.xlsx` `.ppt` `.pptx` `.txt` `.epub` `.cbz` |
| **torrent** | `.torrent` |

> 同时依据 MIME 类型（`video/*`、`audio/*`、`image/*`）分类。`voice` 归入 audio，`sticker` 归入 photo。

## 架构

```
┌──────────────────────────────────────────────────┐
│              单容器 (tg-downloader)                │
│                                                    │
│  ┌─────────────────┐     ┌──────────────────┐    │
│  │  Bot (Telethon)  │     │  Web 管理界面     │    │
│  │  监听群消息 → 下载│     │  FastAPI :8081   │    │
│  │  通知 → DM       │     │  仪表盘/文件/设置 │    │
│  └────────┬────────┘     └──────────────────┘    │
│           │                    │                   │
│           ▼                    ▼                   │
│  ┌──────────────────────────────────────────┐    │
│  │  /downloads/ (持久化)                     │    │
│  │  ├── video/   ├── audio/   ├── photo/    │    │
│  │  ├── document/└── torrents/watch/         │    │
│  └──────────────────────────────────────────┘    │
│                                                    │
│  配置: settings.json  (Web 界面读写)              │
│  会话: sessions/  (Telethon 登录态)               │
│  日志: logs/                                      │
└──────────────────────────────────────────────────┘
         │
         ▼  (外部 qBittorrent)
   ┌──────────────┐
   │  qBittorrent │  ← 用户自行搭建，通过 Web API 连接
   │  Web API     │
   └──────────────┘
```

## 🚀 一键部署

```bash
# 只需 2 条命令：
git clone https://github.com/wenqa1/tg-downloader.git
cd tg-downloader && bash deploy.sh
```

**脚本会自动完成：**

| 步骤 | 说明 |
|------|------|
| ✅ 构建镜像 | `docker build -t tg-downloader ./core` |
| ✅ 创建数据目录 | 自动创建 downloads/sessions/logs/settings |
| ✅ 启动容器 | 映射端口 8081，挂载持久化卷 |
| ✅ 输出后续指引 | 首次登录、Web 管理界面地址 |

> **Windows 用户**：确保 Docker Desktop 已安装，在 Git Bash 中运行 `bash deploy.sh`。

### 手动运行

```bash
# 构建镜像
docker build -t tg-downloader ./core

# 启动容器
docker run -d \
  --name tg-downloader \
  --restart unless-stopped \
  -p 8081:8081 \
  -v $(pwd)/data/downloads:/downloads \
  -v $(pwd)/data/sessions:/app/sessions \
  -v $(pwd)/data/logs:/app/logs \
  -v $(pwd)/data/settings:/app/settings \
  tg-downloader
```

### 首次登录

```bash
docker attach tg-downloader
```

输入短信验证码，按 `Ctrl+P` → `Ctrl+Q` 安全断开。之后启动无需再登录。

## Web 管理界面

启动后访问 `http://你的NASIP:8081`。

| 页面 | 路径 | 功能 |
|------|------|------|
| 📊 **总览** | `/` | 统计卡片、分类占比、最近下载、系统状态 |
| 📁 **文件** | `/files` | 按分类浏览文件、搜索文件 |
| 🧲 **磁力链** | `/torrents` | 连接外部 qBittorrent 查看下载进度 |
| ⚙️ **设置** | `/settings` | **在线配置一切**：API 凭证、运行模式、群 ID、qB 连接 |

> 💡 所有配置通过 Web 界面完成，**无需编辑 .env 文件**。保存后重启 Bot 即可生效。

### API 接口

| 接口 | 说明 |
|------|------|
| `GET /api/stats` | 仪表盘统计数据 |
| `GET /api/files/{category}` | 列出某分类文件（支持 `?search=`） |
| `GET /api/torrents` | 外部 qBittorrent 下载列表 |
| `GET /api/logs` | 最近下载事件 |
| `GET /api/settings` | 获取当前配置 |
| `PUT /api/settings` | 保存配置到 settings.json |

## 配置说明

所有配置通过 Web 界面（`/settings`）完成，保存在 `data/settings/settings.json`。

| 配置项 | 说明 |
|--------|------|
| **运行模式** | User 模式（推荐）或 Bot 模式 |
| **API ID / Hash** | 从 https://my.telegram.org 获取 |
| **手机号** | 闲置副号，用于 Telethon 登录 |
| **Bot Token** | Bot 模式时从 @BotFather 获取 |
| **主人 User ID** | 你的主号 ID（白名单 + 通知接收） |
| **监听群组 Chat ID** | 机器人监听的群 |
| **qB URL / 账号 / 密码** | 连接你已有的 qBittorrent |

> 环境变量（`.env`）仅作为首次部署的引导方式，配置保存后会写入 settings.json。
> `.env` 中的值会覆盖 settings.json，如需完全使用 Web 配置，请清空 .env 中对应项。

## 常用命令

```bash
# 查看日志
docker logs tg-downloader -f

# 重启 Bot（修改配置后）
docker restart tg-downloader

# 停止容器
docker stop tg-downloader

# 更新版本
git pull
docker build -t tg-downloader ./core
docker stop tg-downloader
docker run -d --name tg-downloader --restart unless-stopped \
  -p 8081:8081 \
  -v $(pwd)/data/downloads:/downloads \
  -v $(pwd)/data/sessions:/app/sessions \
  -v $(pwd)/data/logs:/app/logs \
  -v $(pwd)/data/settings:/app/settings \
  tg-downloader
```

## 常见问题

### qBittorrent 连接不上？

1. 确认 qBittorrent 已启用 Web API（设置 → Web UI → 勾选）
2. 在 Web 界面 `/settings` 填入正确的地址（如 `http://192.168.1.100:8080`）
3. 保存后重启容器

### 验证码过期？

```bash
docker stop tg-downloader
docker rm tg-downloader
rm -rf data/sessions/*
# 重新运行容器，然后 docker attach 输入验证码
```

### 如何修改监听群组？

打开 Web 界面 → 设置 → 修改「监听群组 Chat ID」→ 保存 → 重启容器。

也可首次启动时不填群 ID，日志会列出所有可用对话。

## 目录结构

```
tg-downloader/
├── Dockerfile                # 单容器构建
├── docker-compose.yml        # 可选：Docker Compose 方式
├── docker-run.sh             # 一键构建+运行脚本
├── deploy.sh                 # 一键部署脚本
├── .env.example              # 环境变量模板（仅首次引导）
├── .dockerignore
├── .gitignore
├── README.md
├── core/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py           # 主入口（Web + Bot 同进程启动）
│       ├── config.py         # 配置加载（settings.json 优先）
│       ├── helpers.py        # 共享工具函数
│       ├── handlers/         # 消息处理
│       │   ├── file_handler.py
│       │   ├── magnet_handler.py
│       │   └── command_handler.py
│       ├── receivers/
│       │   └── user_receiver.py
│       ├── notifiers/
│       │   └── user_notifier.py
│       ├── downloaders/
│       │   └── qb_client.py
│       ├── organizer/
│       │   └── classifier.py
│       └── web/
│           ├── server.py     # FastAPI 管理界面
│           ├── templates/    # HTML 模板
│           └── static/       # CSS/JS
└── data/                     # 运行时数据（自动生成）
    ├── downloads/
    ├── sessions/
    ├── logs/
    └── settings/
```

## 技术栈

| 组件 | 用途 |
|------|------|
| **Python 3.12** | 运行环境 |
| **Telethon** | MTProto 客户端（无限文件下载） |
| **FastAPI + Uvicorn** | Web 管理界面（同进程运行） |
| **Jinja2** | HTML 模板引擎 |
| **aiohttp** | 异步 HTTP（qBittorrent API） |
| **qBittorrent** | 外部磁力链/种子下载器（用户自行提供） |

## 许可证

MIT
