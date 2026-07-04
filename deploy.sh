#!/usr/bin/env bash
# ============================================
# TG Downloader Bot — 一键部署脚本
# ============================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  TG Downloader Bot — 一键部署${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ---- Check prerequisites ----
command -v docker >/dev/null 2>&1 || {
    echo -e "${RED}[错误] 未安装 Docker，请先安装 Docker${NC}"
    echo "  https://docs.docker.com/engine/install/"
    exit 1
}
command -v docker-compose >/dev/null 2>&1 || {
    echo -e "${YELLOW}[注意] 未找到 docker-compose 命令，尝试 docker compose...${NC}"
    DOCKER_COMPOSE="docker compose"
}

DOCKER_COMPOSE="${DOCKER_COMPOSE:-docker-compose}"
echo -e "${GREEN}[✓] Docker 已安装${NC}"

# ---- Setup .env ----
if [ ! -f .env ]; then
    echo ""
    echo -e "${YELLOW}[配置] 首次部署，需要配置 .env 文件${NC}"
    cp .env.example .env
    echo -e "${YELLOW}  已从 .env.example 创建 .env 文件${NC}"
    echo -e "${YELLOW}  请编辑 .env 文件填入你的配置：${NC}"
    echo -e "${YELLOW}    TELEGRAM_API_ID     — 从 https://my.telegram.org 获取${NC}"
    echo -e "${YELLOW}    TELEGRAM_API_HASH   — 从 https://my.telegram.org 获取${NC}"
    echo -e "${YELLOW}    PHONE_NUMBER        — 闲置副号手机号${NC}"
    echo -e "${YELLOW}    OWNER_USER_ID       — 你的主号 User ID${NC}"
    echo -e "${YELLOW}    QBITTORRENT_PASSWORD— 修改为强密码${NC}"
    echo ""
    echo -e "${YELLOW}  编辑完成后，重新运行本脚本即可启动。${NC}"
    echo -e "${YELLOW}  也可以之后在 Web 管理界面中修改配置。${NC}"
    echo ""
    echo -e "  编辑命令: ${GREEN}nano .env${NC} 或 ${GREEN}vim .env${NC}"
    exit 0
else
    echo -e "${GREEN}[✓] .env 文件已存在${NC}"
fi

# ---- Check required config ----
source .env 2>/dev/null || true
MISSING=""
[ -z "$TELEGRAM_API_ID" ] && MISSING="$MISSING TELEGRAM_API_ID"
[ -z "$TELEGRAM_API_HASH" ] && MISSING="$MISSING TELEGRAM_API_HASH"
[ -z "$PHONE_NUMBER" ] && MISSING="$MISSING PHONE_NUMBER"
[ -z "$OWNER_USER_ID" ] && MISSING="$MISSING OWNER_USER_ID"

if [ -n "$MISSING" ]; then
    echo -e "${YELLOW}[警告] 以下配置项为空：${MISSING}${NC}"
    echo -e "${YELLOW}  服务可以启动，但机器人可能无法正常工作。${NC}"
    echo -e "${YELLOW}  请通过 Web 管理界面或直接编辑 .env 完善配置。${NC}"
fi

# ---- Prepare directories ----
mkdir -p core/sessions core/logs downloads/{video,audio,photo,document,torrents/watch} qbittorrent/config
echo -e "${GREEN}[✓] 目录结构已创建${NC}"

# ---- Pull and build ----
echo ""
echo -e "${BLUE}[构建] 拉取镜像并构建...${NC}"
$DOCKER_COMPOSE pull qbittorrent 2>/dev/null || true
$DOCKER_COMPOSE build --pull
echo -e "${GREEN}[✓] 构建完成${NC}"

# ---- Start services ----
echo ""
echo -e "${BLUE}[启动] 启动所有服务...${NC}"
$DOCKER_COMPOSE up -d
echo -e "${GREEN}[✓] 服务已启动${NC}"

# ---- Show status ----
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  TG Downloader Bot 部署完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "  Web 管理界面: ${GREEN}http://$(hostname -I 2>/dev/null | awk '{print $1}'):8081${NC}"
echo -e "  qBittorrent:   ${GREEN}http://$(hostname -I 2>/dev/null | awk '{print $1}'):8080${NC}"
echo ""
echo -e "${YELLOW}  首次运行需要登录 Telegram 账号：${NC}"
echo -e "  1. ${GREEN}docker attach tg-downloader${NC}"
echo -e "  2. 输入短信验证码"
echo -e "  3. 按 ${GREEN}Ctrl+P${NC} 然后 ${GREEN}Ctrl+Q${NC} 安全断开"
echo ""
echo -e "  查看日志:    ${GREEN}$DOCKER_COMPOSE logs -f tg-downloader${NC}"
echo -e "  重启服务:    ${GREEN}$DOCKER_COMPOSE restart tg-downloader${NC}"
echo -e "  停止服务:    ${GREEN}$DOCKER_COMPOSE down${NC}"
echo -e "  配置管理:    ${GREEN}http://你的NASIP:8081/settings${NC}"
echo ""
echo -e "${YELLOW}  提示: 修改配置后需要重启 tg-downloader 容器生效${NC}"
echo ""
