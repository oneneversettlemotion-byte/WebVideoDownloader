# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[
        ("ffmpeg", "."),
        ("yt-dlp", "."),
    ],
    datas=[
        ("static", "static"),
        ("logo.jpg", "."),
    ],
    hiddenimports=[
        "flask",
        "pkg_resources",
        "webview",
        "webview.platforms.cocoa",
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
    upx=False,
    console=False,
    codesign_identity=None,
)

coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False, upx=False,
    name="VideoDownloader",
)

app = BUNDLE(
    coll,
    name="Video Downloader.app",
    icon="AppIcon.icns",
    bundle_identifier="com.local.videodownloader",
    info_plist={
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        "CFBundleDisplayName": "Video Downloader",
        "CFBundleShortVersionString": "1.1.0",
        "NSRequiresAquaSystemAppearance": False,
    },
)
