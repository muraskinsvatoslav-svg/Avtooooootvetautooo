[app]

# Название приложения
title = Юзербот

# Имя пакета
package.name = userbot
package.domain = org.userbot

# Где лежат исходные файлы
source.dir = .

# Расширения файлов
source.include_exts = py,png,jpg,kv,atlas

# Версия
version = 1.0

# Необходимые библиотеки
requirements = python3,kivy,telethon,pysocks,cryptg

# Ориентация экрана
orientation = portrait
fullscreen = 0

# Разрешения Android
android.permissions = INTERNET,ACCESS_NETWORK_STATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# Настройки SDK/NDK
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 0
