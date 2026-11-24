@echo off
chcp 936 >nul
cd /d "%~dp0"
setlocal enabledelayedexpansion

echo.
echo ==============================================
echo   IP 运营工作台 · 一键安装
echo ==============================================
echo.

rem ---------- 1. 找可用的 Python 3.11 / 3.12 ----------
set "PY="
if defined IPWB_PYTHON if exist "%IPWB_PYTHON%" set "PY=%IPWB_PYTHON%"
if not defined PY if exist "%~dp0python\python.exe" set "PY=%~dp0python\python.exe"
if not defined PY if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined PY if exist "F:\Tools\Python312\python.exe" set "PY=F:\Tools\Python312\python.exe"
if not defined PY (where py >nul 2>nul && set "PY=py -3")
if not defined PY (where python >nul 2>nul && set "PY=python")

set "OK=0"
if defined PY (
  %PY% -c "import sys; sys.exit(0 if sys.version_info[:2] in ((3,11),(3,12)) else 1)" >nul 2>nul
  if not errorlevel 1 set "OK=1"
)
if "%OK%"=="1" goto have_python

rem ---------- 2. 没找到，尝试用内置安装包自动装 ----------
echo 没有找到可用的 Python 3.12。
if not exist "%~dp0installer\python-3.12.10-amd64.exe" goto no_python

echo 正在用内置安装包安装 Python 3.12.10 ...
echo （装到当前用户目录，不需要管理员权限，也不联网）
echo.
"%~dp0installer\python-3.12.10-amd64.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0

set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
if not exist "!PY!" goto install_failed
"!PY!" -c "import sys; sys.exit(0 if sys.version_info[:2] in ((3,11),(3,12)) else 1)" >nul 2>nul
if errorlevel 1 goto install_failed
echo Python 3.12.10 安装完成。
echo.

:have_python
echo 使用 Python：!PY!
echo.
echo [1/2] 安装工作台主程序依赖...
echo       第一次安装需要联网，约下载 1.5GB，可能需要几分钟。
echo.

%PY% -m pip install -r requirements.txt

if errorlevel 1 (
  echo.
  echo [错误] 依赖安装失败，请检查网络后重新运行本文件。
  echo.
  pause
  exit /b 1
)

echo.
echo [1/2] 完成。
echo.

rem ---------- 3. 链接解析服务的独立环境 ----------
echo [2/2] 安装链接解析服务，视频号链接解析要用...
echo.
set "PARSER_DIR=%~dp0tools\media-parser"
if not exist "%PARSER_DIR%\requirements.txt" (
  echo [跳过] 没有找到 tools\media-parser，视频号链接解析将不可用。
  goto done
)

if not exist "%PARSER_DIR%\.venv\Scripts\python.exe" (
  echo 创建独立环境...
  %PY% -m venv "%PARSER_DIR%\.venv"
)

if not exist "%PARSER_DIR%\.venv\Scripts\python.exe" (
  echo [警告] 创建解析环境失败，视频号链接解析将不可用。
  echo        其他功能不受影响，可以先继续用。
  goto done
)

echo 安装解析服务依赖...
"%PARSER_DIR%\.venv\Scripts\python.exe" -m pip install -q --upgrade pip
"%PARSER_DIR%\.venv\Scripts\python.exe" -m pip install -r "%PARSER_DIR%\requirements.txt" tzdata

if errorlevel 1 (
  echo [警告] 解析服务依赖安装失败，多半是网络问题。视频号链接解析暂时不可用。
  echo        其他功能不受影响，可以稍后重新双击本文件再试。
) else (
  echo 解析服务安装完成。
)

goto done

:no_python
echo.
echo [错误] 没有找到 Python 3.12，内置安装包也不在。
echo 请手动安装 Python 3.12：
echo   https://www.python.org/downloads/windows/
echo   找 Latest Python 3.12.x Release，下载 Windows installer 64-bit 版本。
echo   安装时勾选 Add python.exe to PATH。
echo.
pause
exit /b 1

:install_failed
echo.
echo [错误] 内置安装包安装失败。
echo 请手动安装 Python 3.12：
echo   https://www.python.org/downloads/windows/
echo.
pause
exit /b 1

:done
echo.
echo ==============================================
echo   全部完成！
echo.
echo   接下来三步：
echo   1. 双击「启动工作台.cmd」打开工作台
echo   2. 在「设置」页填入 API Key
echo   3. 首次转写视频会自动下载语音模型，约 1.5GB，请保持联网
echo ==============================================
echo.
pause
