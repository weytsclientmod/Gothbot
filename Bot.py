from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta
import re

api_id = 2040
api_hash = "b18441a1ff607e10a989891a5462e627"
bot_token = "8507781595:AAEZNfvzi4CMieBu3y5xNBR3cWCBciBTlrU"
OWNER_ID = 6482245590

app = Client("bot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

apps = {}
questions = {}
banned = set()
muted = {}
waiting_for = {}
reply_mode = {}
mute_data = {}
idea_counter = 1
question_counter = 1

spam_control = {}
spam_warned = {}
SPAM_LIMIT = 10

question_cooldown = {}
idea_cooldown = {}
COOLDOWN_TIME = timedelta(minutes=10)

admins = {OWNER_ID: {"level": 3, "username": "chomikponik", "warns": 0, "trial_start": None, "daily_answers": 0, "daily_reset": None}}
logs = []

CHAT_LINK = "https://t.me/+NhqsDo-qu78xN2I6"
TRIAL_DAILY_LIMIT = 10

def log_action(admin_id, admin_name, action):
    logs.append({
        "time": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "admin": f"@{admin_name}" if admin_name else str(admin_id),
        "action": action
    })
    if len(logs) > 200:
        logs.pop(0)

def get_level(uid):
    return admins.get(uid, {}).get("level", -1)

def is_admin(uid):
    return uid in admins

def is_banned(uid):
    if uid in banned:
        return True
    if uid in muted:
        if muted[uid] == "forever":
            return True
        if datetime.now() < muted[uid]:
            return True
        else:
            del muted[uid]
    return False

def is_spam(uid):
    if is_admin(uid):
        return False
    now = datetime.now()
    if uid not in spam_control or spam_control[uid]["reset"] < now:
        spam_control[uid] = {"count": 1, "reset": now + timedelta(minutes=1)}
        return False
    spam_control[uid]["count"] += 1
    if spam_control[uid]["count"] > SPAM_LIMIT:
        if uid not in spam_warned or spam_warned[uid] < now:
            spam_warned[uid] = now + timedelta(minutes=1)
            return "warn"
        return "block"
    return False

def check_trial_limit(uid):
    if uid not in admins:
        return False
    if admins[uid]["level"] != 0:
        return True
    now = datetime.now()
    if admins[uid].get("daily_reset") is None or admins[uid]["daily_reset"] < now:
        admins[uid]["daily_answers"] = 0
        admins[uid]["daily_reset"] = now + timedelta(hours=24)
    if admins[uid]["daily_answers"] >= TRIAL_DAILY_LIMIT:
        return False
    admins[uid]["daily_answers"] += 1
    return True

def user_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📩 Подать идею для ТГК")],
        [KeyboardButton("🎮 Вопрос по игре")],
        [KeyboardButton("📋 Мои заявки")]
    ], resize_keyboard=True)

def admin_menu(uid):
    lvl = get_level(uid)
    buttons = []
    if lvl >= 0:
        buttons.append([KeyboardButton("🎮 Вопросы по игре")])
    if lvl == 3:
        buttons.append([KeyboardButton("📋 Идеи для ТГК")])
    if lvl >= 0:
        buttons.append([KeyboardButton("👑 Админ-панель")])
    buttons.append([KeyboardButton("📋 Мои истории"), KeyboardButton("📜 Логи")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def back_button():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]])

def parse_mute_time(text):
    text = text.strip().lower()
    if text == "навсегда":
        return "forever"
    match = re.match(r"(\d+)\s*(минут|минута|минуты|час|часа|часов|день|дня|дней|недел|неделя|недели|недель|месяц|месяца|месяцев)", text)
    if not match:
        return None
    num = int(match.group(1))
    unit = match.group(2)
    if unit in ("минут", "минута", "минуты"):
        return timedelta(minutes=num)
    elif unit in ("час", "часа", "часов"):
        return timedelta(hours=num)
    elif unit in ("день", "дня", "дней"):
        return timedelta(days=num)
    elif unit in ("недел", "неделя", "недели", "недель"):
        return timedelta(weeks=num)
    elif unit in ("месяц", "месяца", "месяцев"):
        return timedelta(days=num * 30)
    return None

def format_mute_duration(duration):
    if duration == "forever":
        return "навсегда"
    total_seconds = duration.total_seconds()
    days = int(total_seconds // 86400)
    hours = int((total_seconds % 86400) // 3600)
    minutes = int((total_seconds % 3600) // 60)
    parts = []
    if days:
        parts.append(f"{days} дн.")
    if hours:
        parts.append(f"{hours} ч.")
    if minutes:
        parts.append(f"{minutes} мин.")
    return " ".join(parts) if parts else "0 мин."

# ========== СТАРТ ==========
@app.on_message(filters.command("start"))
async def start(client, message):
    uid = message.from_user.id
    if is_banned(uid):
        await message.reply("Вы заблокированы или заглушены.")
        return
    if is_admin(uid):
        await message.reply("Приветствую, администратор.", reply_markup=admin_menu(uid))
    else:
        await message.reply("Добро пожаловать! Предложи идею для ТГК или задай вопрос по игре.", reply_markup=user_menu())

# ========== ПОЛЬЗОВАТЕЛЬСКИЕ КНОПКИ ==========
@app.on_message(filters.text & filters.regex("^📩 Подать идею для ТГК$"))
async def submit_idea(client, message):
    uid = message.from_user.id
    if is_banned(uid):
        await message.reply("Вы заблокированы или заглушены.")
        return
    if uid not in admins and uid in idea_cooldown:
        remaining = idea_cooldown[uid] - datetime.now()
        if remaining.total_seconds() > 0:
            mins = int(remaining.total_seconds() // 60) + 1
            await message.reply(f"⏳ Ты сможешь подать следующую идею через {mins} мин.")
            return
    waiting_for[uid] = "idea"
    await message.reply("Напиши свою идею для ТГК:", reply_markup=back_button())

@app.on_message(filters.text & filters.regex("^🎮 Вопрос по игре$"))
async def ask_question(client, message):
    uid = message.from_user.id
    if is_banned(uid):
        await message.reply("Вы заблокированы или заглушены.")
        return
    if uid not in admins and uid in question_cooldown:
        remaining = question_cooldown[uid] - datetime.now()
        if remaining.total_seconds() > 0:
            mins = int(remaining.total_seconds() // 60) + 1
            await message.reply(f"⏳ Ты сможешь задать следующий вопрос через {mins} мин.")
            return
    waiting_for[uid] = "question"
    await message.reply("Опиши проблему. Можешь прикрепить фото.", reply_markup=back_button())

@app.on_message(filters.text & filters.regex("^📋 Мои заявки$"))
async def my_stuff(client, message):
    uid = message.from_user.id
    user_ideas = {k: v for k, v in apps.items() if v["user_id"] == uid}
    user_questions = {k: v for k, v in questions.items() if v["user_id"] == uid}
    if not user_ideas and not user_questions:
        await message.reply("У тебя пока ничего нет.", reply_markup=back_button())
        return
    text = ""
    if user_ideas:
        text += "📩 ТВОИ ИДЕИ ДЛЯ ТГК:\n\n"
        for iid, data in user_ideas.items():
            s = "⏳ На рассмотрении" if data["status"] == "pending" else "🤔 На раздумии" if data["status"] == "thinking" else "✅ Принята" if data["status"] == "accepted" else "❌ Отклонена"
            text += f"#{iid}: {data['text'][:40]}... — {s}\n"
    if user_questions:
        text += "\n🎮 ТВОИ ВОПРОСЫ ПО ИГРЕ:\n\n"
        for qid, data in user_questions.items():
            s = "⏳ Ожидает" if data["status"] == "pending" else "✅ Отвечен"
            text += f"#{qid}: {data['text'][:40]}... — {s}\n"
    await message.reply(text, reply_markup=back_button())

# ========== АДМИНСКИЕ КНОПКИ ==========
@app.on_message(filters.text & filters.regex("^📋 Идеи для ТГК$"))
async def active_ideas(client, message):
    if get_level(message.from_user.id) != 3:
        return
    pending = {k: v for k, v in apps.items() if v["status"] == "pending"}
    thinking = {k: v for k, v in apps.items() if v["status"] == "thinking"}
    all_active = {**pending, **thinking}
    if not all_active:
        await message.reply("Нет активных идей для ТГК.", reply_markup=back_button())
        return
    for iid, data in all_active.items():
        status_text = "🤔 На раздумии" if data["status"] == "thinking" else "⏳ Новая"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Принять", callback_data=f"acc_{iid}"),
             InlineKeyboardButton("❌ Отклонить", callback_data=f"rej_{iid}")],
            [InlineKeyboardButton("🤔 На раздумии", callback_data=f"think_{iid}"),
             InlineKeyboardButton("💬 Ответить", callback_data=f"irep_{iid}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ])
        await message.reply(f"📩 Идея для ТГК #{iid} [{status_text}]\nОт: @{data['username']}\nТекст: {data['text']}", reply_markup=kb)

@app.on_message(filters.text & filters.regex("^🎮 Вопросы по игре$"))
async def admin_questions(client, message):
    uid = message.from_user.id
    if get_level(uid) < 0:
        return
    pending = {k: v for k, v in questions.items() if v["status"] == "pending"}
    if not pending:
        await message.reply("Нет активных вопросов по игре.", reply_markup=back_button())
        return
    for qid, data in pending.items():
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💬 Ответить", callback_data=f"qrep_{qid}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")]
        ])
        text = f"🎮 Вопрос по игре #{qid}\nОт: @{data['username']}\nТекст: {data['text']}"
        if data.get("photo"):
            await message.reply_photo(data["photo"], caption=text, reply_markup=kb)
        else:
            await message.reply(text, reply_markup=kb)

@app.on_message(filters.text & filters.regex("^📋 Мои истории$"))
async def my_history(client, message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    uname = message.from_user.username or str(uid)
    my_q = {k: v for k, v in questions.items() if v.get("answered_by") == uname}
    my_i = {k: v for k, v in apps.items() if v.get("processed_by") == uname}
    if not my_q and not my_i:
        await message.reply("Ты пока ничего не обработал.", reply_markup=back_button())
        return
    text = "📋 ТВОЯ ИСТОРИЯ:\n\n"
    if my_q:
        text += "🎮 Вопросы по игре:\n"
        for qid, data in my_q.items():
            text += f"#{qid}: @{data['username']} — {data['text'][:30]}...\n"
    if my_i:
        text += "\n📩 Идеи для ТГК:\n"
        for iid, data in my_i.items():
            text += f"#{iid}: @{data['username']} — {data['text'][:30]}...\n"
    await message.reply(text, reply_markup=back_button())

@app.on_message(filters.text & filters.regex("^📜 Логи$"))
async def show_logs(client, message):
    if not is_admin(message.from_user.id):
        return
    if not logs:
        await message.reply("Логи пусты.", reply_markup=back_button())
        return
    text = "📜 ПОСЛЕДНИЕ ДЕЙСТВИЯ:\n\n"
    for entry in logs[-20:]:
        text += f"[{entry['time']}] {entry['admin']}: {entry['action']}\n"
    await message.reply(text, reply_markup=back_button())

# ========== АДМИН-ПАНЕЛЬ ==========
@app.on_message(filters.text & filters.regex("^👑 Админ-панель$"))
async def admin_panel(client, message):
    uid = message.from_user.id
    lvl = get_level(uid)
    if lvl < 0:
        return
    kb_buttons = [[InlineKeyboardButton("📋 Список админов", callback_data="adm_list")]]
    kb_buttons.append([InlineKeyboardButton("💬 Чат", url=CHAT_LINK)])
    if lvl >= 2:
        kb_buttons.append([InlineKeyboardButton("➕ Добавить админа", callback_data="adm_add")])
        kb_buttons.append([InlineKeyboardButton("🔍 Поиск пользователя", callback_data="search_user")])
    kb_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    kb = InlineKeyboardMarkup(kb_buttons)
    await message.reply("👑 Админ-панель:", reply_markup=kb)

@app.on_callback_query(filters.regex("adm_list"))
async def adm_list(client, callback_query):
    uid = callback_query.from_user.id
    lvl = get_level(uid)
    if lvl < 0:
        await callback_query.answer("Нет доступа.")
        return
    text = "📋 СПИСОК АДМИНОВ:\n\n"
    kb = InlineKeyboardMarkup([])
    for aid, data in admins.items():
        lvl_name = {0: "🔰 Испытательный", 1: "Помощник", 2: "Модер", 3: "Глава"}[data["level"]]
        text += f"@{data['username']} — {lvl_name} | Варны: {data['warns']}/3"
        if data["level"] == 0:
            remaining = TRIAL_DAILY_LIMIT - data.get("daily_answers", 0)
            text += f" | Ответов сегодня: {remaining}/{TRIAL_DAILY_LIMIT}"
        if lvl >= 2 and data["level"] < lvl:
            text += " [Доступен]"
            kb.inline_keyboard.append([InlineKeyboardButton(f"⚙️ @{data['username']}", callback_data=f"admact_{aid}")])
        text += "\n"
    if lvl >= 2:
        kb.inline_keyboard.append([InlineKeyboardButton("➕ Добавить", callback_data="adm_add")])
    kb.inline_keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
    await callback_query.message.reply(text, reply_markup=kb)
    await callback_query.answer()

@app.on_callback_query(filters.regex("adm_add"))
async def adm_add_prompt(client, callback_query):
    if get_level(callback_query.from_user.id) < 2:
        await callback_query.answer("Нет доступа.")
        return
    waiting_for[callback_query.from_user.id] = "add_admin"
    await callback_query.message.reply("Отправь @username пользователя для добавления:", reply_markup=back_button())
    await callback_query.answer()

@app.on_callback_query(filters.regex("search_user"))
async def search_user_prompt(client, callback_query):
    if get_level(callback_query.from_user.id) < 2:
        await callback_query.answer("Нет доступа.")
        return
    waiting_for[callback_query.from_user.id] = "search_user"
    await callback_query.message.reply("Отправь @username пользователя для поиска:", reply_markup=back_button())
    await callback_query.answer()

@app.on_callback_query(filters.regex("back_to_main"))
async def callback_back(client, callback_query):
    uid = callback_query.from_user.id
    waiting_for.pop(uid, None)
    reply_mode.pop(uid, None)
    mute_data.pop(uid, None)
    if is_admin(uid):
        await callback_query.message.reply("Главное меню:", reply_markup=admin_menu(uid))
    else:
        await callback_query.message.reply("Главное меню:", reply_markup=user_menu())
    await callback_query.answer()

# ========== ОБРАБОТЧИК @username ==========
@app.on_message(filters.text & filters.regex("^@"))
async def handle_username(client, message):
    uid = message.from_user.id
    mode = waiting_for.get(uid)
    if mode not in ("add_admin", "search_user"):
        return
    target_uname = message.text.replace("@", "").strip()

    if mode == "add_admin":
        if get_level(uid) < 2:
            await message.reply("Нет доступа.", reply_markup=back_button())
            waiting_for.pop(uid, None)
            return
        target_uid = None
        for aid, adata in admins.items():
            if adata["username"].lower() == target_uname.lower():
                target_uid = aid
                break
        if target_uid:
            await message.reply("Этот пользователь уже админ.", reply_markup=back_button())
            waiting_for.pop(uid, None)
            return
        for qid, qdata in questions.items():
            if qdata.get("username", "").lower() == target_uname.lower():
                target_uid = qdata["user_id"]
                break
        if not target_uid:
            for iid, idata in apps.items():
                if idata.get("username", "").lower() == target_uname.lower():
                    target_uid = idata["user_id"]
                    break
        if not target_uid:
            try:
                found = await app.get_users(target_uname)
                if found:
                    target_uid = found.id
            except:
                pass
        if not target_uid:
            await message.reply("Пользователь не найден. Пусть сначала напишет /start боту.", reply_markup=back_button())
            waiting_for.pop(uid, None)
            return
        waiting_for[uid] = "add_admin_level"
        mute_data[uid] = {"target_uid": target_uid, "target_uname": target_uname}
        await message.reply(f"Выбери уровень для @{target_uname}:\n0 — Испытательный (10 ответов/24ч)\n1 — Помощник (вопросы)\n2 — Модер (вопросы + управление)\nОтправь цифру 0, 1 или 2.", reply_markup=back_button())

    elif mode == "search_user":
        if get_level(uid) < 2:
            await message.reply("Нет доступа.", reply_markup=back_button())
            waiting_for.pop(uid, None)
            return
        target_uid = None
        for qid, qdata in questions.items():
            if qdata.get("username", "").lower() == target_uname.lower():
                target_uid = qdata["user_id"]
                break
        if not target_uid:
            for iid, idata in apps.items():
                if idata.get("username", "").lower() == target_uname.lower():
                    target_uid = idata["user_id"]
                    break
        if not target_uid:
            for aid, adata in admins.items():
                if adata["username"].lower() == target_uname.lower():
                    target_uid = aid
                    break
        if not target_uid:
            try:
                found = await app.get_users(target_uname)
                if found:
                    target_uid = found.id
            except:
                pass
        if not target_uid:
            await message.reply("Пользователь не найден.", reply_markup=back_button())
            waiting_for.pop(uid, None)
            return
        muted_text = ""
        if target_uid in banned:
            muted_text = "\n🚫 Забанен"
        elif target_uid in muted:
            if muted[target_uid] == "forever":
                muted_text = "\n🔇 Заглушен навсегда"
            else:
                rem = muted[target_uid] - datetime.now()
                if rem.total_seconds() > 0:
                    muted_text = f"\n🔇 Заглушен до {muted[target_uid].strftime('%d.%m.%Y %H:%M')}"
        is_adm = "👑 Админ" if target_uid in admins else "👤 Пользователь"
        kb_buttons = []
        if target_uid not in banned:
            kb_buttons.append([InlineKeyboardButton("🚫 Заблокировать", callback_data=f"banuser_{target_uid}")])
        else:
            kb_buttons.append([InlineKeyboardButton("✅ Разбанить", callback_data=f"unbanuser_{target_uid}")])
        if target_uid not in muted:
            kb_buttons.append([InlineKeyboardButton("🔇 Заглушить", callback_data=f"muteuser_{target_uid}")])
        else:
            kb_buttons.append([InlineKeyboardButton("🔊 Размутить", callback_data=f"unmuteuser_{target_uid}")])
        kb_buttons.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_main")])
        kb = InlineKeyboardMarkup(kb_buttons)
        await message.reply(f"🔍 Найден: @{target_uname} ({is_adm}){muted_text}", reply_markup=kb)
        waiting_for.pop(uid, None)

# ========== ОБРАБОТКА ТЕКСТА ==========
@app.on_message(filters.text & ~filters.command("start") & ~filters.regex("^📩|^🎮|^📋|^👑|^📜|^@"))
async def handle_text(client, message):
    global idea_counter, question_counter
    uid = message.from_user.id
    if is_banned(uid):
        return

    spam_status = is_spam(uid)
    if spam_status == "warn":
        await message.reply("Эй, не так быстро! Помедленнее, я не успеваю.")
        return
    elif spam_status == "block":
        return

    # Выбор уровня админа
    if waiting_for.get(uid) == "add_admin_level":
        try:
            lvl = int(message.text.strip())
            if lvl not in (0, 1, 2):
                raise ValueError
        except:
            await message.reply("Отправь 0, 1 или 2.", reply_markup=back_button())
            return
        data = mute_data.pop(uid, {})
        target_uid = data.get("target_uid")
        target_uname = data.get("target_uname")
        if not target_uid:
            await message.reply("Ошибка. Начни заново.", reply_markup=back_button())
            waiting_for.pop(uid, None)
            return
        admins[target_uid] = {"level": lvl, "username": target_uname, "warns": 0, "trial_start": datetime.now() if lvl == 0 else None, "daily_answers": 0, "daily_reset": datetime.now() + timedelta(hours=24) if lvl == 0 else None}
        log_action(uid, message.from_user.username, f"Добавил админа @{target_uname} уровня {lvl}")
        lvl_name = {0: "Испытательный", 1: "Помощник", 2: "Модер"}[lvl]
        try:
            await client.send_message(target_uid, f"🎉 Поздравляем! Вы назначены администратором бота.\nУровень: {lvl_name}\nИспользуйте /start для обновления меню.")
        except:
            pass
        await message.reply(f"✅ @{target_uname} добавлен как {lvl_name}.", reply_markup=back_button())
        waiting_for.pop(uid, None)
        return

    # Ответ админа юзеру
    if uid in reply_mode:
        mode = reply_mode[uid]
        if mode["type"] == "idea_reply":
            await client.send_message(apps[mode["id"]]["user_id"], f"📩 Ответ на твою идею для ТГК:\n\n{message.text}")
            await message.reply("Ответ отправлен. Можешь отправить ещё или нажми «Назад».", reply_markup=back_button())
            log_action(uid, message.from_user.username, f"Ответил на идею #{mode['id']}")
        elif mode["type"] == "question_reply":
            if not check_trial_limit(uid):
                await message.reply("Ты исчерпал лимит ответов на сегодня (10/24ч). Жди сброса или повышения.", reply_markup=back_button())
                return
            await client.send_message(questions[mode["id"]]["user_id"], f"🎮 Ответ на твой вопрос по игре:\n\n{message.text}")
            await message.reply("Ответ отправлен. Можешь отправить ещё или нажми «Назад».", reply_markup=back_button())
            log_action(uid, message.from_user.username, f"Ответил на вопрос #{mode['id']} (осталось ответов: {TRIAL_DAILY_LIMIT - admins[uid].get('daily_answers', 0)})")
        return

    # Время заглушения
    if waiting_for.get(uid) == "waiting_mute_time":
        data = mute_data.get(uid, {})
        target_uid = data.get("target_uid")
        target_uname = data.get("target_uname")
        duration = parse_mute_time(message.text)
        if duration is None:
            await message.reply("Не понял формат. Примеры: '10 минут', '2 часа', '1 день', '3 недели', 'навсегда'.", reply_markup=back_button())
            return
        mute_str = "навсегда" if duration == "forever" else format_mute_duration(duration)
        if duration == "forever":
            muted[target_uid] = "forever"
        else:
            muted[target_uid] = datetime.now() + duration
        try:
            await client.send_message(target_uid, f"🔇 Вы заглушены в боте на {mute_str}.")
        except:
            pass
        await message.reply(f"🔇 @{target_uname} заглушен на {mute_str}.", reply_markup=back_button())
        log_action(uid, message.from_user.username, f"Заглушил @{target_uname} на {mute_str}")
        waiting_for.pop(uid, None)
        mute_data.pop(uid, None)
        return

    if is_admin(uid):
        return

    # Юзер отправляет идею/вопрос
    mode = waiting_for.get(uid)
    if mode == "idea":
        iid = idea_counter
        idea_counter += 1
        apps[iid] = {"user_id": uid, "username": message.from_user.username or "без username", "text": message.text, "status": "pending"}
        await message.reply(f"✅ Твоя идея для ТГК #{iid} принята.", reply_markup=user_menu())
        await client.send_message(OWNER_ID, f"🔔 Новая ИДЕЯ ДЛЯ ТГК #{iid} от @{apps[iid]['username']}!\nТекст: {message.text}")
        if uid not in admins:
            idea_cooldown[uid] = datetime.now() + COOLDOWN_TIME
        waiting_for.pop(uid, None)
    elif mode == "question":
        qid = question_counter
        question_counter += 1
        questions[qid] = {"user_id": uid, "username": message.from_user.username or "без username", "text": message.text, "photo": None, "status": "pending"}
        await message.reply(f"✅ Твой вопрос по игре #{qid} принят.", reply_markup=user_menu())
        for aid in admins:
            if admins[aid]["level"] >= 0:
                await client.send_message(aid, f"🔔 Новый ВОПРОС ПО ИГРЕ #{qid} от @{questions[qid]['username']}!\nТекст: {message.text}")
        if uid not in admins:
            question_cooldown[uid] = datetime.now() + COOLDOWN_TIME
        waiting_for.pop(uid, None)
    elif not is_admin(uid):
        await message.reply("Используй кнопки меню для взаимодействия с ботом.", reply_markup=user_menu())

# ========== ФОТО ==========
@app.on_message(filters.photo)
async def handle_photo(client, message):
    global question_counter
    uid = message.from_user.id
    if is_banned(uid):
        return
    if waiting_for.get(uid) == "question":
        caption = message.caption or "Без описания"
        qid = question_counter
        question_counter += 1
        questions[qid] = {"user_id": uid, "username": message.from_user.username or "без username", "text": caption, "photo": message.photo.file_id, "status": "pending"}
        await message.reply(f"✅ Твой вопрос по игре #{qid} с фото принят.", reply_markup=user_menu())
        for aid in admins:
            if admins[aid]["level"] >= 0:
                await client.send_photo(aid, message.photo.file_id, caption=f"🔔 Новый ВОПРОС ПО ИГРЕ #{qid} от @{questions[qid]['username']}\nТекст: {caption}")
        if uid not in admins:
            question_cooldown[uid] = datetime.now() + COOLDOWN_TIME
        waiting_for.pop(uid, None)
    else:
        await message.reply("Сначала нажми «🎮 Вопрос по игре» чтобы отправить фото.", reply_markup=user_menu())

# ========== CALLBACK ==========
@app.on_callback_query()
async def callback_handler(client, callback_query):
    uid = callback_query.from_user.id
    data = callback_query.data

    if data.startswith("acc_"):
        if get_level(uid) != 3:
            await callback_query.answer("Только глава.")
            return
        iid = int(data.split("_")[1])
        apps[iid]["status"] = "accepted"
        apps[iid]["processed_by"] = callback_query.from_user.username or str(uid)
        await client.send_message(apps[iid]["user_id"], f"✅ Твоя идея для ТГК #{iid} ПРИНЯТА!")
        await callback_query.message.edit_text(callback_query.message.text + "\n\n✅ ПРИНЯТО")
        log_action(uid, callback_query.from_user.username, f"Принял идею #{iid}")

    elif data.startswith("rej_"):
        if get_level(uid) != 3:
            await callback_query.answer("Только глава.")
            return
        iid = int(data.split("_")[1])
        apps[iid]["status"] = "rejected"
        apps[iid]["processed_by"] = callback_query.from_user.username or str(uid)
        await client.send_message(apps[iid]["user_id"], f"❌ Твоя идея для ТГК #{iid} отклонена.")
        await callback_query.message.edit_text(callback_query.message.text + "\n\n❌ ОТКЛОНЕНО")
        log_action(uid, callback_query.from_user.username, f"Отклонил идею #{iid}")

    elif data.startswith("think_"):
        if get_level(uid) != 3:
            await callback_query.answer("Только глава.")
            return
        iid = int(data.split("_")[1])
        if apps[iid]["status"] == "thinking":
            apps[iid]["status"] = "pending"
            await callback_query.message.edit_text(callback_query.message.text.replace("🤔 На раздумии", "⏳ Новая"))
        else:
            apps[iid]["status"] = "thinking"
            await callback_query.message.edit_text(callback_query.message.text.replace("⏳ Новая", "🤔 На раздумии"))
        log_action(uid, callback_query.from_user.username, f"Статус идеи #{iid}: {'На раздумии' if apps[iid]['status'] == 'thinking' else 'Новая'}")

    elif data.startswith("irep_"):
        if get_level(uid) != 3:
            await callback_query.answer("Только глава.")
            return
        iid = int(data.split("_")[1])
        reply_mode[uid] = {"type": "idea_reply", "id": iid}
        await callback_query.message.reply("Напиши ответ. Нажми «Назад» когда закончишь.", reply_markup=back_button())

    elif data.startswith("qrep_"):
        if get_level(uid) < 0:
            return
        if not check_trial_limit(uid):
            await callback_query.answer("Лимит ответов на сегодня исчерпан (10/24ч).")
            return
        qid = int(data.split("_")[1])
        questions[qid]["status"] = "answered"
        questions[qid]["answered_by"] = callback_query.from_user.username or str(uid)
        reply_mode[uid] = {"type": "question_reply", "id": qid}
        await callback_query.message.reply("Напиши ответ. Нажми «Назад» когда закончишь.", reply_markup=back_button())

    elif data.startswith("banuser_"):
        if get_level(uid) < 2:
            await callback_query.answer("Нет доступа.")
            return
        target_uid = int(data.split("_")[1])
        target_uname = "пользователь"
        for q in questions.values():
            if q["user_id"] == target_uid:
                target_uname = q["username"]
                break
        banned.add(target_uid)
        muted.pop(target_uid, None)
        try:
            await client.send_message(target_uid, "🚫 Вы заблокированы в боте.")
        except:
            pass
        log_action(uid, callback_query.from_user.username, f"Заблокировал @{target_uname}")
        await callback_query.message.reply(f"🚫 @{target_uname} заблокирован.", reply_markup=back_button())

    elif data.startswith("unbanuser_"):
        if get_level(uid) < 2:
            await callback_query.answer("Нет доступа.")
            return
        target_uid = int(data.split("_")[1])
        banned.discard(target_uid)
        try:
            await client.send_message(target_uid, "✅ Вы разблокированы в боте.")
        except:
            pass
        log_action(uid, callback_query.from_user.username, f"Разбанил @{target_uid}")
        await callback_query.message.reply("✅ Пользователь разбанен.", reply_markup=back_button())

    elif data.startswith("muteuser_"):
        if get_level(uid) < 2:
            await callback_query.answer("Нет доступа.")
            return
        target_uid = int(data.split("_")[1])
        target_uname = "пользователь"
        for q in questions.values():
            if q["user_id"] == target_uid:
                target_uname = q["username"]
                break
        waiting_for[uid] = "waiting_mute_time"
        mute_data[uid] = {"target_uid": target_uid, "target_uname": target_uname}
        await callback_query.message.reply(f"На сколько заглушить @{target_uname}?\nПримеры: '10 минут', '2 часа', '3 дня', '1 неделя', 'навсегда'.", reply_markup=back_button())

    elif data.startswith("unmuteuser_"):
        if get_level(uid) < 2:
            await callback_query.answer("Нет доступа.")
            return
        target_uid = int(data.split("_")[1])
        muted.pop(target_uid, None)
        try:
            await client.send_message(target_uid, "🔊 Вы размучены в боте.")
        except:
            pass
        log_action(uid, callback_query.from_user.username, f"Размутил @{target_uid}")
        await callback_query.message.reply("✅ Пользователь размучен.", reply_markup=back_button())

    elif data.startswith("admact_"):
        if get_level(uid) < 2:
            await callback_query.answer("Нет доступа.")
            return
        _, target_uid_str = data.split("_", 1)
        target_uid = int(target_uid_str)
        my_lvl = get_level(uid)
        target_lvl = get_level(target_uid)
        if my_lvl <= target_lvl:
            await callback_query.answer("Недостаточно прав.")
            return
        target_uname = admins[target_uid]["username"]
        warns = admins[target_uid]["warns"]
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⚠️ Варн ({warns}/3)", callback_data=f"warn_{target_uid}")],
            [InlineKeyboardButton("🚫 Уволить", callback_data=f"fire_{target_uid}")],
            [InlineKeyboardButton("🔙 Назад", callback_data="adm_list")]
        ])
        await callback_query.message.reply(f"Действия с @{target_uname} (уровень {target_lvl}):", reply_markup=kb)

    elif data.startswith("warn_"):
        if get_level(uid) < 2:
            await callback_query.answer("Нет доступа.")
            return
        target_uid = int(data.split("_")[1])
        my_lvl = get_level(uid)
        target_lvl = get_level(target_uid)
        if my_lvl <= target_lvl:
            await callback_query.answer("Недостаточно прав.")
            return
        target_uname = admins[target_uid]["username"]
        admins[target_uid]["warns"] += 1
        warns = admins[target_uid]["warns"]
        log_action(uid, callback_query.from_user.username, f"Выдал варн @{target_uname} ({warns}/3)")
        try:
            await client.send_message(target_uid, f"⚠️ Администратор @{callback_query.from_user.username} выдал вам варн ({warns}/3). При 3 варнах вы будете уволены.")
        except:
            pass
        if warns >= 3:
            del admins[target_uid]
            log_action(uid, callback_query.from_user.username, f"Уволил @{target_uname} (3 варна)")
            try:
                await client.send_message(target_uid, "🚫 Вы уволены с должности администратора (3 варна).")
            except:
                pass
            await callback_query.message.reply(f"🚫 @{target_uname} получил 3/3 варнов и уволен.", reply_markup=back_button())
        else:
            await callback_query.message.reply(f"⚠️ @{target_uname} получил варн ({warns}/3). Уведомление отправлено.", reply_markup=back_button())

    elif data.startswith("fire_"):
        if get_level(uid) < 2:
            await callback_query.answer("Нет доступа.")
            return
        target_uid = int(data.split("_")[1])
        my_lvl = get_level(uid)
        target_lvl = get_level(target_uid)
        if my_lvl <= target_lvl:
            await callback_query.answer("Недостаточно прав.")
            return
        target_uname = admins[target_uid]["username"]
        del admins[target_uid]
        log_action(uid, callback_query.from_user.username, f"Уволил @{target_uname}")
        try:
            await client.send_message(target_uid, "🚫 Вы уволены с должности администратора.")
        except:
            pass
        await callback_query.message.reply(f"🚫 @{target_uname} уволен. Уведомление отправлено.", reply_markup=back_button())

    await callback_query.answer()

app.run()
