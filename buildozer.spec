[app]

# Название твоего приложения
title = Юзербот

# Имя пакета
package.name = userbot
package.domain = org.userbot

# Где лежат исходные файлы
source.dir = .

# Какие расширения файлов включать в сборку
source.include_exts = py,png,jpg,kv,atlas

# Версия приложения
version = 1.0

# Необходимые библиотеки Python (Kivy, Telethon и сетевые зависимости)
requirements = python3,kivy,telethon,pysocks,cryptg

# Ориентация экрана (портретная)
orientation = portrait

# Полноэкранный режим (0 — выключен, строка состояния видна)
fullscreen = 0

# Разрешения приложения для работы с сетью и памятью
android.permissions = INTERNET,ACCESS_NETWORK_STATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# Версии Android SDK и NDK для стабильной сборки через GitHub Actions
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a

[buildozer]

# Уровень логирования (2 — подробный)
log_level = 2

# Предупреждение о рутованных правах (оставляем 0)
warn_on_root = 0
