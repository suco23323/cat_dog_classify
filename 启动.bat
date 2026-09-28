@echo off
chcp 65001 >nul
setlocal
set "ROOT=%~dp0"

echo ============================================
echo   猫狗分类识别 - 一键启动
echo ============================================

if not exist "%ROOT%backend\main.py" (
    echo [错误] 未找到 backend\main.py,请确认本脚本位于工程根目录。
    pause
    exit /b 1
)
if not exist "%ROOT%tools\node\npm.cmd" (
    echo [错误] 未找到 tools\node\npm.cmd,Node.js 免安装版缺失。
    pause
    exit /b 1
)
if not exist "D:\anaconda\Scripts\activate.bat" (
    echo [错误] 未找到 conda 的 activate.bat,请检查 D:\anaconda 是否存在。
    pause
    exit /b 1
)

echo [1/3] 启动后端服务 http://127.0.0.1:8000 ...
start "cat-dog-backend" cmd /k "call D:\anaconda\Scripts\activate.bat pytorch_paoge && cd /d %ROOT%backend && uvicorn main:app --host 127.0.0.1 --port 8000"

echo [2/3] 启动前端服务 http://localhost:5173 ...
start "cat-dog-frontend" cmd /k "set PATH=%ROOT%tools\node;%PATH% && cd /d %ROOT%frontend && npm run dev"

echo [3/3] 等待服务就绪后打开浏览器 ...
timeout /t 6 /nobreak >nul
start "" http://localhost:5173

echo.
echo [完成] 后端(8000)与前端(5173)已启动,浏览器将自动打开页面。
echo 提示:关闭 cat-dog-backend 与 cat-dog-frontend 两个窗口即可停止服务;
echo       若提示端口被占用,请先关闭占用进程后重试。
timeout /t 8 /nobreak >nul
endlocal