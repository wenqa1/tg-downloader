#!/usr/bin/env bash
# ============================================
# TG Downloader Bot — 单容器一键运行脚本
# ============================================
# 用法:
#   bash docker-run.sh              # 构建并启动
#   bash docker-run.sh --build      # 强制重新构建
#   bash docker-run.sh --stop       # 停止容器
# ============================================
set -e

NAME="tg-downloader"
PORT="${PORT:-8081}"
DATA_DIR="${DATA_DIR:-./data}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Handle commands
case "${1:-}" in
    --stop|-s)
        echo -e "${BLUE}[停止] 停止容器...${NC}"
        docker stop "$NAME" 2>/dev/null || true
        docker rm "$NAME" 2>/dev/null || true
        echo -e "${GREEN}[✓] 已停止${NC}"
        exit 0
        ;;
    --help|-h)
        echo "用法: bash docker-run.sh [选项]"
        echo "选项:"
        echo "  --build    强制重新构建镜像"
        echo "  --stop     停止容器"
        echo "  --help     显示此帮助"
        exit 0
        ;;
esac

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  TG Downloader Bot — 单容器运行${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ---- Check Docker ----
command -v docker >/dev/null 2>&1 || {
    echo -e "${RED}[错误] 未安装 Docker${NC}"
    exit 1
}
echo -e "${GREEN}[✓] Docker 已安装${NC}"

# ---- Create data directories ----
mkdir -p "$DATA_DIR"/{downloads,sessions,logs,settings}
echo -e "${GREEN}[✓] 数据目录已创建: $DATA_DIR${NC}"

# ---- Build image ----
if [ "${1:-}" = "--build" ] || ! docker image inspect tg-downloader >/dev/null 2>&1; then
    echo ""
    echo -e "${BLUE}[构建] 构建 Docker 镜像...${NC}"
    docker build -t tg-downloader ./core
    echo -e "${GREEN}[✓] 镜像构建完成${NC}"
else
    echo -e "${GREEN}[✓] 镜像已存在（使用 --build 强制重建）${NC}"
fi

# ---- Stop existing ----
docker stop "$NAME" >/dev/null 2>&1 && echo -e "${YELLOW}[停止] 旧容器已停止${NC}" || true
docker rm "$NAME" >/dev/null 2>&1 || true

# ---- Run container ----
echo ""
echo -e "${BLUE}[启动] 启动容器...${NC}"

docker run -d \
    --name "$NAME" \
    --restart unless-stopped \
    -p "$PORT":8081 \
    -v "$(pwd)/$DATA_DIR/downloads":/downloads \
    -v "$(pwd)/$DATA_DIR/sessions":/app/sessions \
    -v "$(pwd)/$DATA_DIR/logs":/app/logs \
    -v "$(pwd)/$DATA_DIR/settings":/app/settings \
    -e WEB_PORT=8081 \
    -e WEB_HOST=0.0.0.0 \
    tg-downloader

echo -e "${GREEN}[✓] 容器已启动${NC}"

# ---- Show info ----
IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}  TG Downloader Bot 运行中！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "  Web 管理界面: ${GREEN}http://localhost:$PORT${NC}"
[ -n "$IP" ] && echo -e "  局域网访问:    ${GREEN}http://$IP:$PORT${NC}"
echo ""
echo -e "  首次登录: ${YELLOW}docker attach $NAME${NC}"
echo -e "  查看日志: ${YELLOW}docker logs $NAME -f${NC}"
echo -e "  重启容器: ${YELLOW}docker restart $NAME${NC}"
echo -e "  停止容器: ${YELLOW}bash docker-run.sh --stop${NC}"
echo ""
echo -e "${YELLOW}  提示: 配置通过 Web 界面完成，无需编辑 .env 文件${NC}"
echo ""
