@echo off
chcp 936 >nul
cd /d "%~dp0"

rem 按顺序寻找 Python：环境变量指定 -> 项目内自带 -> 用户目录 3.12 -> 本机已知位置 -> py -> python
set "PY="
if defined IPWB_PYTHON if exist "%IPWB_PYTHON%" set "PY=%IPWB_PYTHON%"
if not defined PY if exist "%~dp0python\python.exe" set "PY=%~dp0python\python.exe"
if not defined PY if exist "%LocalAppData%\Programs\Python\Python312\python.exe" set "PY=%LocalAppData%\Programs\Python\Python312\python.exe"
if not defined PY if exist "F:\Tools\Python312\python.exe" set "PY=F:\Tools\Python312\python.exe"
if not defined PY (where py >nul 2>nul && set "PY=py -3")
if not defined PY (where python >nul 2>nul && set "PY=python")

if not defined PY (
  echo.
  echo [未找到 Python] 请先双击 install.bat 自动安装。
  echo.
  pause
  exit /b 1
)

rem 版本必须是 3.11 或 3.12
%PY% -c "import sys; sys.exit(0 if sys.version_info[:2] in ((3,11),(3,12)) else 1)" >nul 2>nul
if errorlevel 1 (
  echo.
  echo [Python 版本不对] 需要 3.11 或 3.12。
  echo 请双击 install.bat，它会自动安装合适的版本。
  echo.
  pause
  exit /b 1
)

%PY% -c "import fastapi, uvicorn, multipart" >nul 2>nul
if errorlevel 1 (
  echo.
  echo [缺少依赖] 请先双击 install.bat 安装依赖。
  echo.
  pause
  exit /b 1
)

%PY% "%~dp0app.py"
pause
