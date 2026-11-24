@echo off
chcp 936 >nul
cd /d "%~dp0"
setlocal enabledelayedexpansion

echo.
echo ==============================================
echo   IP 运营工作台 · 更新到最新版
echo ==============================================
echo.

set "GIT="
if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=%ProgramFiles%\Git\cmd\git.exe"
if not defined GIT if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "GIT=%ProgramFiles(x86)%\Git\cmd\git.exe"
if not defined GIT if exist "%LocalAppData%\Programs\Git\cmd\git.exe" set "GIT=%LocalAppData%\Programs\Git\cmd\git.exe"
if not defined GIT (where git >nul 2>nul && set "GIT=git")

if not defined GIT goto no_git
if not exist ".git" goto no_repo

echo 正在检查更新，请稍候...
echo.
"%GIT%" pull

if errorlevel 1 goto pull_failed

echo.
echo 更新完成。你的 Key、登录态、历史数据都在 data\ 里，没有被覆盖。
echo.

rem ---------- 依赖有变化时自动补装 ----------
set "PY="
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined PY if exist "F:\Tools\Python312\python.exe" set "PY=F:\Tools\Python312\python.exe"
if not defined PY (where py >nul 2>nul && set "PY=py -3")
if not defined PY (where python >nul 2>nul && set "PY=python")

if not defined PY goto launch_hint
echo 正在检查依赖是否有变化...
%PY% -m pip install -q -r requirements.txt
echo 依赖检查完成。
echo.

:launch_hint
echo 双击「启动工作台.cmd」即可使用。
echo.
pause
exit /b 0

:no_git
echo.
echo [无法更新] 没有找到 git。
echo 请双击 install.bat，它会自动装好 git。
echo.
pause
exit /b 1

:no_repo
echo.
echo [无法更新] 这个文件夹不是 git 版本，可能是用压缩包解压的。
echo 请先双击「切换为自动更新.bat」，只需要做一次。
echo.
pause
exit /b 1

:pull_failed
echo.
echo [更新失败] 常见原因：
echo   1. 网络问题，检查能不能打开 github.com
echo   2. 你改过代码文件，和云端冲突
echo.
echo 如果反复失败，把这张截图发给负责人。
echo.
pause
exit /b 1
