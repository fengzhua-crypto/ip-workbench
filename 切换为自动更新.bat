@echo off
chcp 936 >nul
cd /d "%~dp0"
setlocal enabledelayedexpansion

echo ==============================================
echo   IP 运营工作台 · 切换为自动更新模式
echo.
echo   只需要做一次。
echo   做完以后，双击「更新.bat」就能更新。
echo.
echo   本操作会做三件事：
echo     1. 把当前文件夹变成 git 版本
echo     2. 用云端最新代码覆盖代码文件
echo     3. 保留 data 文件夹，Key 和拆解数据不受影响
echo ==============================================
echo.
pause

set "GIT="
if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=%ProgramFiles%\Git\cmd\git.exe"
if not defined GIT if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "GIT=%ProgramFiles(x86)%\Git\cmd\git.exe"
if not defined GIT if exist "%LocalAppData%\Programs\Git\cmd\git.exe" set "GIT=%LocalAppData%\Programs\Git\cmd\git.exe"
if not defined GIT (where git >nul 2>nul && set "GIT=git")
if not defined GIT goto no_git

if exist ".git" goto already

echo [1/3] 备份数据库...
if exist "data\app.db" copy /y "data\app.db" "data\app.db.bak" >nul
echo        完成。
echo.

echo [2/3] 连接云端仓库...
"%GIT%" init >nul 2>nul
"%GIT%" remote add origin https://github.com/fengzhua-crypto/ip-workbench.git
"%GIT%" fetch origin master
if errorlevel 1 goto fetch_failed
echo        完成。
echo.

echo [3/3] 用云端代码覆盖代码文件...
"%GIT%" reset --hard origin/master
if errorlevel 1 goto fetch_failed
"%GIT%" branch -M master
"%GIT%" branch --set-upstream-to=origin/master master >nul 2>nul
echo        完成。
echo.

echo ==============================================
echo   切换成功！
echo.
echo   你的 data 文件夹没有任何改动。
echo.
echo   接下来两步：
echo   1. 双击 install.bat，补装这一次的依赖
echo   2. 双击「启动工作台.cmd」打开工作台
echo.
echo   以后有更新，双击「更新.bat」即可。
echo ==============================================
echo.
pause
exit /b 0

:already
echo 这个文件夹已经是自动更新模式了，直接拉取最新代码...
echo.
"%GIT%" pull
echo.
echo 完成。双击「启动工作台.cmd」即可使用。
pause
exit /b 0

:no_git
echo.
echo [无法继续] 没有找到 git。
echo 请先双击 install.bat，它会自动装好 git，然后再运行本文件。
echo.
pause
exit /b 1

:fetch_failed
echo.
echo [失败] 没能从云端拿到代码，常见原因：
echo   1. 网络问题，检查能不能打开 github.com
echo   2. git 版本太旧
echo.
echo 你的 data 文件夹没有被改动，可以放心重试。
echo 如果反复失败，把这张截图发给负责人。
echo.
pause
exit /b 1
