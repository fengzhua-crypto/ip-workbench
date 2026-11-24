@echo off
chcp 936 >nul
cd /d "%~dp0"
setlocal enabledelayedexpansion

echo.
echo ==============================================
echo   IP 运营工作台 · 一键安装
echo ==============================================
echo.

rem ---------- 1. 检查 git（只影响「更新.bat」，缺了也照样能跑） ----------
set "GIT="
if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=%ProgramFiles%\Git\cmd\git.exe"
if not defined GIT if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "GIT=%ProgramFiles(x86)%\Git\cmd\git.exe"
if not defined GIT if exist "%LocalAppData%\Programs\Git\cmd\git.exe" set "GIT=%LocalAppData%\Programs\Git\cmd\git.exe"
if not defined GIT (where git >nul 2>nul && set "GIT=git")

if defined GIT (
  echo [1/4] git 已安装，跳过。
  goto have_git
)

echo [1/4] 没有找到 git，它是用来一键更新工作台的。
if not exist "%~dp0installer\Git-2.56.1-64-bit.exe" goto no_git

echo        正在用内置安装包装 git，请耐心等待，不要关窗口...
echo.
start /wait "" "%~dp0installer\Git-2.56.1-64-bit.exe" /VERYSILENT /NORESTART /NOCANCEL /SP- /o:PathOption=Cmd

set "GIT="
if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=%ProgramFiles%\Git\cmd\git.exe"
if not defined GIT if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set "GIT=%ProgramFiles(x86)%\Git\cmd\git.exe"
if not defined GIT if exist "%LocalAppData%\Programs\Git\cmd\git.exe" set "GIT=%LocalAppData%\Programs\Git\cmd\git.exe"

if defined GIT (
  echo         git 安装完成。
  goto have_git
)

:no_git
echo.
echo [提示] git 没有装上。工作台照样能用，只是「更新.bat」暂时用不了。
echo        可以手动安装：https://git-scm.com/download/win 一路点 Next
echo.

:have_git
echo.

rem ---------- 2. 找可用的 Python 3.11 / 3.12 ----------
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
echo [2/4] 安装工作台主程序依赖...
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
echo [2/4] 完成。
echo.

rem ---------- 3. 链接解析服务的独立环境 ----------
echo [3/4] 安装链接解析服务，视频号链接解析要用...
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

rem ---------- 4. 图文笔记的图片识别环境 ----------
echo.
echo [4/4] 安装图片文字识别环境，图文笔记拆解要用...
echo.
set "OCR_DIR=%~dp0tools\ocr"
if not exist "%OCR_DIR%\ocr_batch.py" (
  echo [跳过] 没有找到 tools\ocr，图文笔记的图片文字将无法识别。
  goto done
)

if not exist "%OCR_DIR%\.venv\Scripts\python.exe" (
  echo 创建独立环境...
  %PY% -m venv "%OCR_DIR%\.venv"
)

if not exist "%OCR_DIR%\.venv\Scripts\python.exe" (
  echo [警告] 创建识别环境失败，图文笔记的图片文字将无法识别。
  echo        其他功能不受影响，可以先继续用。
  goto done
)

echo 安装识别依赖...
"%OCR_DIR%\.venv\Scripts\python.exe" -m pip install -q --upgrade pip
"%OCR_DIR%\.venv\Scripts\python.exe" -m pip install -q rapidocr-onnxruntime

if errorlevel 1 (
  echo [警告] 识别依赖安装失败，多半是网络问题。图文笔记的图片文字暂时识别不了。
  echo        其他功能不受影响，可以稍后重新双击本文件再试。
) else (
  echo 识别环境安装完成。
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
