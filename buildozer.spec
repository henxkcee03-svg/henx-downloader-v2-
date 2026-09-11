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
#
# The KivMob zip URL (not a plain PyPI name) is how KivMob's own docs say
# to install it — it's a thin Python/pyjnius wrapper, not a compiled
# recipe, so buildozer just pip-installs it like any pure-Python package.
# This is the single most likely thing to break the build: ad SDKs need
# real Gradle/AndroidX wiring (see android.gradle_dependencies and
# android.meta_data below) that most other requirements here don't, and
# that combination has a history of gradlew failures for other KivMob
# users on GitHub. If a build fails after adding this line, removing it
# (and the kivmob-specific lines below) gets you back to a known-working
# build while you debug ads separately — nothing else in the app depends
# on it (see the ADS_AVAILABLE guard in main.py).
requirements = hostpython3==3.11.8,python3==3.11.8,kivy==2.3.0,plyer,yt-dlp,certifi,chardet,idna,urllib3,requests,https://github.com/MichaelStott/KivMob/archive/refs/heads/master.zip

# tools/ holds generate_license.py, a standalone desktop script for
# minting premium license keys — it has nothing to do with the app
# itself and must never ship inside the APK.
source.exclude_dirs = tools

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

# ---- AdMob (KivMob) ----
# The Google Mobile Ads SDK, pulled in as a Gradle dependency rather than
# a python-for-android recipe. android.enable_androidx is required — the
# Ads SDK is AndroidX-only. p4a.branch=master matches KivMob's own setup
# instructions; p4a's stable release branch has been reported to not play
# well with this combination.
#
# Fixed: this used to point at com.google.firebase:firebase-ads, which
# Google's own docs confirm is an empty/legacy alias artifact — it hasn't
# been the real SDK for years and was fully discontinued as of Mobile
# Ads SDK v24. That's very likely what was behind the app crashing when
# offline: an unstable ad dependency plus (fixed separately in main.py)
# ad requests firing before connectivity had even been checked. Pinned
# to 22.6.0 rather than the newest release, since v24+ made breaking API
# changes that KivMob's bundled Java bridge — last updated years ago —
# almost certainly doesn't account for.
android.gradle_dependencies = com.google.android.gms:play-services-ads:22.6.0
android.enable_androidx = True
p4a.branch = master
# This is Google's published TEST AdMob App ID — safe to build with, but
# it only ever serves Google's placeholder test ads. Swap it for your own
# AdMob App ID (from your AdMob console, not an ad unit ID) before a real
# release, or real ads will never show. ADMOB_APP_ID/BANNER_ID/
# INTERSTITIAL_ID in main.py must be updated to match.
android.meta_data = com.google.android.gms.ads.APPLICATION_ID=ca-app-pub-3940256099942544~3347511713

[buildozer]
log_level = 2
warn_on_root = 1
