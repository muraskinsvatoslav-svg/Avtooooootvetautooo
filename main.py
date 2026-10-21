# -*- coding: utf-8 -*-
import os
import time
import asyncio
import threading
import random
import re
from datetime import datetime
import zoneinfo

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock

from telethon import TelegramClient, events, functions, types

MEDIA_DIR = "media_downloads"
os.makedirs(MEDIA_DIR, exist_ok=True)

# Универсальные встроенные ключи Telegram под капотом (пользователю вводить не нужно)
DEFAULT_API_ID = 6
DEFAULT_API_HASH = "eb06d4abfb49dc3eeb1aeb98ae0f581e"

# Глобальные переменные состояния юзербота
AFK_RU_DEFAULT = "Привет! Сейчас я занят и не могу ответить, чуть позже обязательно отпишу."
is_afk = True
global_muted = False
ghost_mode_enabled = True
dnd_mode_enabled = False
dnd_start_time = 0

blacklisted_users = set()
vip_users = set()
muted_chats = set()
known_chats = set()
bad_words = {"спам", "скам", "заработок", "казино", "бесплатно", "крипта", "инвестиции", "доход"}
snippets = {
    "/pc": "🖥 Конфигурация: Xiaomi Pad 6 | Snapdragon 870 | Android APK",
    "/status": "🟢 Система юзербота работает в штатном режиме.",
}

active_potato_games = {}
client = None
bot_client = None
phone_code_future = None


# --- ЭКРАН 1: Настройка токена и ника ---
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=25, spacing=15)
        
        layout.add_widget(Label(text="[b]ZONAR: Шаг 1 из 3[/b]\nНастройка бота и ника", markup=True, font_size=20, halign="center"))

        layout.add_widget(Label(text="Токен вашего управляющего бота:"))
        self.bot_token = TextInput(text="8547908899:AAEB-cR-j-H7M8VOTZ6BZ7OplIevQfLsTNA", multiline=False)
        layout.add_widget(self.bot_token)

        layout.add_widget(Label(text="Ваш ник для анимаций (например, NARCIS):"))
        self.nickname = TextInput(text="NARCIS", multiline=False)
        layout.add_widget(self.nickname)

        next_btn = Button(text="Далее ➔", background_color=(0.1, 0.6, 0.3, 1), size_hint_y=None, height=50)
        next_btn.bind(on_press=self.go_to_phone)
        layout.add_widget(next_btn)

        self.add_widget(layout)

    def go_to_phone(self, instance):
        app = App.get_running_app()
        app.config_data['bot_token'] = self.bot_token.text.strip()
        app.config_data['nickname'] = self.nickname.text.strip() or "NARCIS"
        app.screen_manager.current = 'phone_screen'


# --- ЭКРАН 2: Ввод номера телефона ---
class PhoneScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=25, spacing=15)
        
        layout.add_widget(Label(text="[b]ZONAR: Шаг 2 из 3[/b]\nВведите номер телефона", markup=True, font_size=20, halign="center"))
        layout.add_widget(Label(text="Укажите номер в международном формате\n(например: +380XXXXXXXXX):", font_size=14))

        self.phone_input = TextInput(hint_text="+380...", multiline=False, font_size=18)
        layout.add_widget(self.phone_input)

        send_btn = Button(text="Отправить код в Telegram ➔", background_color=(0.1, 0.6, 0.3, 1), size_hint_y=None, height=50)
        send_btn.bind(on_press=self.request_code)
        layout.add_widget(send_btn)

        self.add_widget(layout)

    def request_code(self, instance):
        phone = self.phone_input.text.strip()
        if not phone.startswith("+"):
            return
        app = App.get_running_app()
        app.config_data['phone'] = phone
        app.screen_manager.current = 'code_screen'
        
        threading.Thread(target=app.start_telegram_auth, daemon=True).start()


# --- ЭКРАН 3: Ввод кода подтверждения ---
class CodeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=25, spacing=15)
        
        layout.add_widget(Label(text="[b]ZONAR: Шаг 3 из 3[/b]\nВведите код из Telegram", markup=True, font_size=20, halign="center"))
        layout.add_widget(Label(text="Код подтверждения пришел вам\nв официальном аккаунте Telegram:", font_size=14))

        self.code_input = TextInput(hint_text="12345", multiline=False, font_size=22)
        layout.add_widget(self.code_input)

        confirm_btn = Button(text="Подтвердить и войти ✅", background_color=(0.1, 0.6, 0.3, 1), size_hint_y=None, height=50)
        confirm_btn.bind(on_press=self.submit_code)
        layout.add_widget(confirm_btn)

        self.add_widget(layout)

    def submit_code(self, instance):
        code = self.code_input.text.strip()
        app = App.get_running_app()
        if app.phone_code_future and not app.phone_code_future.done():
            app.phone_code_future.set_result(code)


# --- ЭКРАН 4: Панель управления ---
class ControlPanelScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = ScrollView()
        layout = BoxLayout(orientation='vertical', padding=20, spacing=15, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))

        layout.add_widget(Label(text="[b]🟢 ЮЗЕРБОТ УСПЕШНО ЗАПУЩЕН![/b]", markup=True, font_size=18, size_hint_y=None, height=40))
        
        self.status_lbl = Label(text="Статус: Работает в фоне", size_hint_y=None, height=30)
        layout.add_widget(self.status_lbl)

        grid_btns = GridLayout(cols=2, spacing=10, size_hint_y=None, height=140)
        
        self.btn_afk = Button(text="AFK: ВКЛ 💤")
        self.btn_afk.bind(on_press=lambda x: self.toggle_flag("afk"))
        grid_btns.add_widget(self.btn_afk)

        self.btn_dnd = Button(text="DND: ВЫКЛ 🔔")
        self.btn_dnd.bind(on_press=lambda x: self.toggle_flag("dnd"))
        grid_btns.add_widget(self.btn_dnd)

        self.btn_mute = Button(text="Мут всех: ВЫКЛ 🔊")
        self.btn_mute.bind(on_press=lambda x: self.toggle_flag("mute"))
        grid_btns.add_widget(self.btn_mute)

        self.btn_ghost = Button(text="Стелс: ВКЛ 👻")
        self.btn_ghost.bind(on_press=lambda x: self.toggle_flag("ghost"))
        grid_btns.add_widget(self.btn_ghost)

        layout.add_widget(grid_btns)
        root.add_widget(layout)
        self.add_widget(root)

    def toggle_flag(self, flag_type):
        global is_afk, global_muted, ghost_mode_enabled, dnd_mode_enabled, dnd_start_time
        if flag_type == "afk":
            is_afk = not is_afk
            self.btn_afk.text = f"AFK: {'ВКЛ 💤' if is_afk else 'ВЫКЛ 🟢'}"
        elif flag_type == "dnd":
            dnd_mode_enabled = not dnd_mode_enabled
            if dnd_mode_enabled:
                dnd_start_time = time.time()
            self.btn_dnd.text = f"DND: {'ВКЛ 🔕' if dnd_mode_enabled else 'ВЫКЛ 🔔'}"
        elif flag_type == "mute":
            global_muted = not global_muted
            self.btn_mute.text = f"Мут всех: {'ВКЛ 🔇' if global_muted else 'ВЫКЛ 🔊'}"
        elif flag_type == "ghost":
            ghost_mode_enabled = not ghost_mode_enabled
            self.btn_ghost.text = f"Стелс: {'ВКЛ 👻' if ghost_mode_enabled else 'ВЫКЛ 👁'}"


# --- ГЛАВНОЕ ПРИЛОЖЕНИЕ ---
class UserbotApp(App):
    def build(self):
        self.title = "ZONAR Userbot"
        self.config_data = {}
        self.phone_code_future = None

        self.screen_manager = ScreenManager()
        
        self.screen_manager.add_widget(LoginScreen(name='login_screen'))
        self.screen_manager.add_widget(PhoneScreen(name='phone_screen'))
        self.screen_manager.add_widget(CodeScreen(name='code_screen'))
        self.screen_manager.add_widget(ControlPanelScreen(name='control_screen'))

        return self.screen_manager

    def start_telegram_auth(self):
        asyncio.run(self.async_telegram_login())

    async def async_telegram_login(self):
        global client, bot_client, phone_code_future
        try:
            bot_token = self.config_data['bot_token']
            phone = self.config_data['phone']

            client = TelegramClient('session_' + phone.replace('+', ''), DEFAULT_API_ID, DEFAULT_API_HASH)
            await client.connect()

            if not await client.is_user_authorized():
                await client.send_code_request(phone)
                
                phone_code_future = asyncio.get_running_loop().create_future()
                code = await phone_code_future
                
                try:
                    await client.sign_in(phone, code)
                except Exception:
                    pass

            me = await client.get_me()
            owner_id = me.id

            if bot_token:
                bot_client = TelegramClient('bot_session_' + phone.replace('+', ''), DEFAULT_API_ID, DEFAULT_API_HASH)
                await bot_client.start(bot_token=bot_token)
                @bot_client.on(events.NewMessage(pattern='/start'))
                async def start_handler(event):
                    if event.sender_id == owner_id:
                        await event.respond("🛠 **ZONAR Userbot успешно управляется через APK!**")

            self.register_all_handlers(client, bot_client, owner_id)
            Clock.schedule_once(lambda dt: setattr(self.screen_manager, 'current', 'control_screen'), 0)

            await client.run_until_disconnected()

        except Exception as e:
            print(f"[ERROR] Ошибка авторизации: {e}")

    def register_all_handlers(self, tg_client, bc, owner_id):
        @tg_client.on(events.NewMessage(outgoing=True))
        async def handle_outgoing(event):
            global is_afk, muted_chats, known_chats, active_potato_games
            text = event.raw_text.strip()
            text_lower = text.lower()

            if event.is_private and event.chat_id not in known_chats:
                known_chats.add(event.chat_id)
                asyncio.create_task(self.animate_narcis_and_matrix(tg_client, chat_id=event.chat_id))

            if text_lower in ["картошка", "картоха"]:
                chat_id = event.chat_id
                if chat_id in active_potato_games:
                    del active_potato_games[chat_id]
                await event.edit("🥔 **ГОРЯЧАЯ КАРТОШКА!** Отправьте точку (`.`), чтобы начать игру!")
                active_potato_games[chat_id] = {"started": False, "holder_id": None, "holder_name": None, "timer": 20, "msg_obj": event.message}
                return

            if event.chat_id in active_potato_games:
                game = active_potato_games[event.chat_id]
                me = await tg_client.get_me()
                if not game["started"] and text == ".":
                    game["started"] = True
                    game["holder_id"] = me.id
                    game["holder_name"] = me.first_name or "Я"
                    game["timer"] = 20
                    asyncio.create_task(self.run_potato_game(tg_client, event.chat_id))
                    return

            if text_lower in [".m", ".м", ".matrix", ".n", ".н"]:
                asyncio.create_task(self.animate_narcis_and_matrix(tg_client, msg_obj=event.message))
                return
            if text_lower in [".heart", ".сердце"]:
                asyncio.create_task(self.animate_heart(event.message))
                return

        @tg_client.on(events.NewMessage(incoming=True))
        async def incoming_pipeline(event):
            global ghost_mode_enabled, global_muted, muted_chats, blacklisted_users, dnd_mode_enabled
            if dnd_mode_enabled and event.is_private:
                try: await event.delete()
                except Exception: pass
                return
            if is_afk and event.is_private:
                try: await event.respond(AFK_RU_DEFAULT)
                except Exception: pass

    async def animate_narcis_and_matrix(self, tg_client, msg_obj=None, chat_id=None):
        custom_name = self.config_data.get('nickname', 'NARCIS').upper()
        letters_db = {
            "N": ["█▄ █", "█ ▀█", "█  █", "▀  ▀"], "A": [" ▄▀█ ", "█▀█▀█", "█  ██", "▀  ▀▀"],
            "R": ["█▀█", "█▀▄", "█ █", "▀ ▀"], "C": ["█▀▀", "█  ", "█▄▄", "▀▀▀"],
            "I": ["█", "█", "█", "▀"], "S": ["█▀ ", "▄█ ", "██ ", "▀▀ "],
            "V": ["█  █", "█  █", " █ █ ", "  ▀  "], "T": ["▀█▀", " █ ", " █ ", " ▀ "],
            "O": ["▄▀█", "█ █", "█ █", "▀▀▀"], "M": ["█ █", "████", "█ █", "▀ ▀"],
            "E": ["█▀▀", "█▀ ", "█▄▄", "▀▀▀"], "D": ["█▀█", "█ █", "█ █", "▀▀█"],
            "B": ["█▀█", "█▀█", "█▄█", "▀▀▀"], "L": ["█  ", "█  ", "█▄▄", "▀▀▀"],
            "K": ["█ █", "█▀ ", "█ █", "▀ ▀"], "Y": ["█ █", " █ ", " █ ", " ▀ "],
            "P": ["█▀█", "█▀█", "█  ", "▀  "], "H": ["█ █", "███", "█ █", "▀ ▀"],
            "U": ["█ █", "█ █", "█ █", "▀▀▀"], "W": ["█ █", "█ █", "█▄█", "▀ ▀"],
        }
        order = list(custom_name)
        if msg_obj is None and chat_id is not None:
            try: msg_obj = await tg_client.send_message(chat_id, "```\n █\n```")
            except Exception: return
        for i in range(1, len(order) + 1):
            current_keys = order[:i]
            lines = [" ".join([letters_db.get(k, [" █ ", " █ ", " █ ", " ▀ "])[line_idx] for k in current_keys]) for line_idx in range(4)]
            frame = f"```\n" + "\n".join(lines) + "\n─────────────────\n0101 1010\n```"
            try:
                await msg_obj.edit(frame)
                await asyncio.sleep(0.3)
            except Exception:
                break

    async def animate_heart(self, msg_obj):
        custom_name = self.config_data.get('nickname', 'NARCIS').upper()
        for h in ["❤️", "💖", "❤️‍🔥"]:
            try:
                await msg_obj.edit(f"{h} {custom_name} {h}")
                await asyncio.sleep(0.4)
            except Exception:
                break

    async def run_potato_game(self, tg_client, chat_id):
        while chat_id in active_potato_games:
            game = active_potato_games[chat_id]
            if not game["started"]:
                await asyncio.sleep(0.5)
                continue
            game["timer"] -= 1
            if game["timer"] <= 0:
                try: await game["msg_obj"].edit(f"💥 **КАРТОШКА ВЗОРВАЛАСЬ!**")
                except Exception: pass
                del active_potato_games[chat_id]
                break
            await asyncio.sleep(1.0)


if __name__ == '__main__':
    UserbotApp().run()
