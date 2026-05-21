# -*- mode: python ; coding: utf-8 -*-
# Windows 打包配置

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[
        ("ffmpeg.exe", "."),
        ("yt-dlp.exe", "."),
    ],
    datas=[
        ("static", "static"),
        ("logo.jpg", "."),
    ],
    hiddenimports=[
        "flask",
        "pkg_resources",
        "webview",
        "webview.platforms.winforms",
        "clr",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="VideoDownloader",
    debug=False,
    strip=False,
    upx=True,
    console=False,          # 不显示黑色命令行窗口
    icon="AppIcon.ico",     # Windows 图标
    version=None,
)

coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=True,
    name="VideoDownloader",
)
