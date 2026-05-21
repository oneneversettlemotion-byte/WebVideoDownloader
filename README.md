# Video Downloader

支持 YouTube、Bilibili、站酷、抖音、小红书等 1000+ 平台的桌面视频下载工具。

## 功能特性

- 🎬 支持 1000+ 视频网站（YouTube / Bilibili / 站酷 / 抖音 / 小红书等）
- 📊 实时进度条、速度、ETA 显示
- 📂 自定义保存位置（原生文件夹选择弹窗）
- 🔄 yt-dlp 启动时自动更新，保持最新版本
- 🖥️ 支持 macOS + Windows 双端
- 🎨 深色毛玻璃 UI 风格

## 使用方法

1. 启动 App
2. 粘贴视频链接
3. 点击「📂 浏览…」选择保存位置（默认 ~/Downloads）
4. 点击「⬇ 开始下载」

## 本地开发

```bash
# 安装依赖
pip3.11 install flask pywebview yt-dlp pillow

# 启动
cd WebVideoDownloader_App
python3.11 main.py
```

## 打包

```bash
# macOS
python3.11 -m PyInstaller build.spec --distpath dist --workpath build --noconfirm

# Windows（在 Windows 机器上运行）
双击 build_windows.bat
```

## 项目上下文

完整的技术文档和上下文见 [PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md)。
