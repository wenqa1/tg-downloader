@echo off
chcp 65001 >nul
REM ============================================
REM TG Downloader Bot — Windows 一键部署脚本
REM ============================================

echo ========================================
echo   TG Downloader Bot — 一键部署
echo ========================================
echo.

REM Check Docker
where docker >nul 2>&1 || (
    echo [错误] 未安装 Docker，请先安装 Docker Desktop
    echo   https://docs.docker.com/desktop/windows/install/
    pause
    exit /b 1
)
echo [✓] Docker 已安装

REM Check docker-compose
where docker-compose >nul 2>&1 || (
    echo [注意] 未找到 docker-compose，使用 docker compose
    set DOCKER_COMPOSE=docker compose
)
if not defined DOCKER_COMPOSE set DOCKER_COMPOSE=docker-compose

REM Setup .env
if not exist .env (
    echo.
    echo [配置] 首次部署，正在创建 .env 文件...
    copy .env.example .env >nul
    echo [黄色] 已从 .env.example 创建 .env 文件
    echo [黄色] 请编辑 .env 文件填入你的配置：
    echo   TELEGRAM_API_ID     - 从 https://my.telegram.org 获取
    echo   TELEGRAM_API_HASH   - 从 https://my.telegram.org 获取
    echo   PHONE_NUMBER        - 闲置副号手机号
    echo   OWNER_USER_ID       - 你的主号 User ID
    echo   QBITTORRENT_PASSWORD - 修改为强密码
    echo.
    echo 编辑完成后，重新运行本脚本即可启动。
    echo 也可以之后在 Web 管理界面中修改配置。
    echo.
    pause
    exit /b 0
) else (
    echo [✓] .env 文件已存在
)

REM Prepare directories
if not exist core\sessions mkdir core\sessions
if not exist core\logs mkdir core\logs
if not exist core\settings mkdir core\settings
if not exist downloads\video mkdir downloads\video
if not exist downloads\audio mkdir downloads\audio
if not exist downloads\photo mkdir downloads\photo
if not exist downloads\document mkdir downloads\document
if not exist downloads\torrents\watch mkdir downloads\torrents\watch
if not exist qbittorrent\config mkdir qbittorrent\config
echo [✓] 目录结构已创建

REM Pull and build
echo.
echo [构建] 拉取镜像并构建...
%DOCKER_COMPOSE% pull qbittorrent 2>nul
%DOCKER_COMPOSE% build --pull

REM Start
echo.
echo [启动] 启动所有服务...
%DOCKER_COMPOSE% up -d

REM Done
echo.
echo ========================================
echo   TG Downloader Bot 部署完成！
echo ========================================
echo.
echo   Web 管理界面: http://localhost:8081
echo   qBittorrent:   http://localhost:8080
echo.
echo   首次运行需要登录 Telegram 账号：
echo   1. docker attach tg-downloader
echo   2. 输入短信验证码
echo   3. 按 Ctrl+P 然后 Ctrl+Q 安全断开
echo.
echo   查看日志: %DOCKER_COMPOSE% logs -f tg-downloader
echo   重启服务: %DOCKER_COMPOSE% restart tg-downloader
echo   停止服务: %DOCKER_COMPOSE% down
echo   配置管理: http://localhost:8081/settings
echo.
pause
