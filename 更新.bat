@echo off
chcp 936 >nul
cd /d "%~dp0"

echo.
echo ==============================================
echo   IP 运营工作台 · 更新到最新版
echo ==============================================
echo.

git pull

if errorlevel 1 (
  echo.
  echo [更新失败] 常见原因：
  echo   1. 没装 git，请看「安装说明.md」第二步
  echo   2. 网络问题，检查能不能打开 github.com
  echo   3. 你改过代码文件，和云端冲突
  echo.
  pause
  exit /b 1
)

echo.
echo 更新完成！双击「启动工作台.cmd」即可使用。
echo 你的 Key、登录态、历史数据都在 data\ 里，不会被覆盖。
echo.
pause
