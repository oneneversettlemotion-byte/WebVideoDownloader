@echo off
chcp 65001 >nul
:: 切换到脚本所在目录（防止从 System32 运行 PyInstaller）
cd /d "%~dp0"
title Video Downloader - Windows 打包脚本
echo.
echo ========================================
echo  Video Downloader Windows 打包工具
echo ========================================
echo.

:: ── 1. 找 Python ────────────────────────────────────────────
set PYTHON=

:: 先试 PATH 里有没有
where python >nul 2>&1
if not errorlevel 1 (
    set PYTHON=python
    goto :found_python
)

:: 再试常见安装路径
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "C:\Python311\python.exe"
    "C:\Python312\python.exe"
    "C:\Program Files\Python311\python.exe"
    "C:\Program Files\Python312\python.exe"
    "C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python311\python.exe"
) do (
    if exist %%P (
        set PYTHON=%%P
        goto :found_python
    )
)

:: 用 py 启动器
where py >nul 2>&1
if not errorlevel 1 (
    set PYTHON=py -3
    goto :found_python
)

echo [错误] 未找到 Python！
echo.
echo 请先安装 Python 3.11 或以上版本：
echo   下载地址: https://www.python.org/downloads/
echo   安装时务必勾选 "Add Python to PATH"
echo.
pause
exit /b 1

:found_python
for /f "tokens=*" %%i in ('%PYTHON% --version 2^>^&1') do set PYVER=%%i
echo [OK] 找到 Python: %PYVER%  ^(%PYTHON%^)

:: ── 2. 安装依赖 ─────────────────────────────────────────────
echo.
echo [1/5] 安装 Python 依赖（首次较慢，请耐心等待）...
%PYTHON% -m pip install -q flask pywebview pyinstaller yt-dlp pillow
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络连接
    pause & exit /b 1
)
echo [OK] 依赖安装完成

:: ── 3. 下载 ffmpeg.exe ──────────────────────────────────────
echo.
echo [2/5] 检查 ffmpeg...
if exist ffmpeg.exe (
    echo [OK] ffmpeg.exe 已存在，跳过下载
) else (
    echo 正在下载 ffmpeg.exe（约 100MB，请耐心等待）...
    powershell -NoProfile -Command "& { $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile 'ffmpeg_tmp.zip' }"
    if errorlevel 1 (
        echo [错误] ffmpeg 自动下载失败，请手动操作：
        echo   1. 浏览器打开: https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
        echo   2. 解压后找到 ffmpeg.exe，复制到本目录
        echo   3. 重新运行此脚本
        pause & exit /b 1
    )
    echo 解压 ffmpeg.exe...
    powershell -NoProfile -Command "& { Add-Type -AssemblyName System.IO.Compression.FileSystem; $z=[System.IO.Compression.ZipFile]::OpenRead('ffmpeg_tmp.zip'); $entry=$z.Entries | Where-Object {$_.Name -eq 'ffmpeg.exe'} | Select-Object -First 1; [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry,'ffmpeg.exe',$true); $z.Dispose() }"
    del ffmpeg_tmp.zip 2>nul
    if exist ffmpeg.exe (
        echo [OK] ffmpeg.exe 下载完成
    ) else (
        echo [错误] ffmpeg.exe 解压失败，请手动放置 ffmpeg.exe 到本目录后重试
        pause & exit /b 1
    )
)

:: ── 4. 下载 yt-dlp.exe ──────────────────────────────────────
echo.
echo [3/5] 检查 yt-dlp...
if exist yt-dlp.exe (
    echo [OK] yt-dlp.exe 已存在，跳过下载
) else (
    echo 正在下载 yt-dlp.exe...
    powershell -NoProfile -Command "& { $ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe' -OutFile 'yt-dlp.exe' }"
    if errorlevel 1 (
        echo [错误] yt-dlp 下载失败，请手动下载：
        echo   https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe
        echo   下载后放到本目录，重新运行脚本
        pause & exit /b 1
    )
    echo [OK] yt-dlp.exe 下载完成
)

:: ── 5. 生成 Windows 图标 .ico ────────────────────────────────
echo.
echo [4/5] 生成 Windows 图标...
if exist AppIcon.ico (
    echo [OK] AppIcon.ico 已存在，跳过
) else (
    %PYTHON% -c "from PIL import Image; img=Image.open('logo.jpg').convert('RGBA'); img.save('AppIcon.ico',format='ICO',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)]); print('OK')" 2>&1
    if not exist AppIcon.ico (
        echo [警告] 图标生成失败，使用默认图标继续
        echo. > AppIcon.ico
    ) else (
        echo [OK] AppIcon.ico 生成成功
    )
)

:: ── 6. PyInstaller 打包 ─────────────────────────────────────
echo.
echo [5/5] 开始打包（约 2-5 分钟）...
%PYTHON% -m PyInstaller build_windows.spec --distpath dist_win --workpath build_win --noconfirm
if errorlevel 1 (
    echo.
    echo [错误] 打包失败！请截图以上错误信息。
    pause & exit /b 1
)

echo.
echo ========================================
echo  ✅ 打包完成！
echo.
echo  输出目录: dist_win\VideoDownloader\
echo  主程序:   dist_win\VideoDownloader\VideoDownloader.exe
echo.
echo  发送方式：将 dist_win\VideoDownloader\ 整个文件夹
echo  压缩成 zip 发给同事，对方解压后双击 .exe 运行即可。
echo ========================================
echo.
pause
