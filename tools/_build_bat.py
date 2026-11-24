"""生成 GBK 编码的 Windows 批处理文件（临时构建脚本）。

为什么用脚本文件而不是命令行内联：
Git Bash（MSYS2）会对命令行参数里的 `nul` 做 POSIX 路径转换，把它改成 `/dev/null`，
写进批处理就成了非法命令。放在文件里执行可以完全避开。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INSTALL = r"""@echo off
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
  echo [1/3] git 已安装，跳过。
  goto have_git
)

echo [1/3] 没有找到 git，它是用来一键更新工作台的。
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
echo [2/3] 安装工作台主程序依赖...
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
echo [2/3] 完成。
echo.

rem ---------- 3. 链接解析服务的独立环境 ----------
echo [3/3] 安装链接解析服务，视频号链接解析要用...
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
"""

LAUNCH = r"""@echo off
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
"""

UPDATE = r"""@echo off
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
"""

SWITCH = r"""@echo off
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
"""

for name, body in (("install.bat", INSTALL),
                   ("启动工作台.cmd", LAUNCH),
                   ("更新.bat", UPDATE),
                   ("切换为自动更新.bat", SWITCH)):
    text = body.replace("\r\n", "\n").replace("\n", "\r\n")
    path = ROOT / name
    path.write_bytes(text.encode("gbk"))
    print(f"{name}: 已写入 GBK，{len(text.encode('gbk'))} 字节")
