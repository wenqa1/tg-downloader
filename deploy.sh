#!/usr/bin/env bash
# ============================================
# TG Downloader Bot — 一键部署脚本
# 单容器运行，所有配置通过 Web 界面完成
# ============================================
set -e

cd "$(dirname "$0")"

echo "========================================"
echo "  TG Downloader Bot — 一键部署"
echo "  单容器 · Web 界面管理配置"
echo "========================================"
echo ""

# ---- Build ----
echo "[构建] 构建 Docker 镜像..."
docker build -t tg-downloader ./core
echo "[✓] 构建完成"
echo ""

# ---- Run ----
echo "[启动] 启动容器..."
bash docker-run.sh
