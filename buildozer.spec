[app]

# ---- App identity ----
title = Henx Downloader
package.name = henxdownloader
package.domain = org.henx

# ---- Source ----
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0

# ---- Requirements ----
# Trimmed to packages with reliable Android build recipes.
# pycryptodomex / brotli / websockets / mutagen were removed: they're
# optional yt-dlp extras with no working python-for-android recipe under
# those names, and were the cause of the first build failure.
#
# python3 AND hostpython3 are both pinned to 3.11.8. Buildozer builds
# two separate Pythons — one that runs during the build itself
# (hostpython3) and one that ships on the phone (python3) — and they
# must match exactly. Pinning only python3 left hostpython3 to default
# to a bleeding-edge 3.14.2, which is what caused the "should have
# same version as hostpython3, 3.11.8 != 3.14.2" failure. Both are
# pinned now so they match.
# plyer added for the native Android share sheet ("Share App"). It's a
# widely-used, well-supported recipe in python-for-android (unlike the
# pycryptodomex/brotli/websockets packages removed earlier, which had no
# working recipe) — this shouldn't reopen the earlier build issues.
requirements = hostpython3==3.11.8,python3==3.11.8,kivy==2.3.0,plyer,yt-dlp,certifi,chardet,idna,urllib3,requests

orientation = portrait
fullscreen = 0
# icon.png — a dark, glowing rounded badge (near-black gradient
# background, thin blue-to-teal rim) with a download arrow + tray
# glyph, matching the Android status-bar download icon. Buildozer
# resizes it for the various Android icon densities automatically.
icon.filename = %(source.dir)s/icon.png

# Native presplash — shown by Android while the app is loading, before
# any Python/Kivy code runs. Set to a plain black background with the
# icon centered, matching the in-app splash so the two blend together
# instead of flashing a mismatched default icon/white screen first.
# Using the exact unquoted hex format from Buildozer's own official
# example (a quoted/named-color format has caused build failures for
# other people, per a known Buildozer GitHub issue).
presplash.filename = %(source.dir)s/presplash.png
android.presplash_color = #000000

# ---- Android permissions ----
# INTERNET: required to download
# WRITE/READ_EXTERNAL_STORAGE: required to save files to /sdcard/Download
# POST_NOTIFICATIONS added for the new notification feature. On Android
# 13+ this permission must be explicitly granted at runtime, not just
# declared here — the OS will prompt the person the first time a
# notification tries to fire; if they deny it, notifications just won't
# show (silently, by design — this won't crash anything).
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,POST_NOTIFICATIONS,VIBRATE

# ---- Android build config ----
android.api = 33
android.minapi = 21
android.ndk = 25b
# Building one architecture first to prove the build works and to keep
# build time down. Add ", armeabi-v7a" back once this succeeds if you
# need to support older 32-bit devices too.
android.archs = arm64-v8a
android.allow_backup = True
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
