import logging
import os
import json
import unicodedata
from functools import wraps
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    BotCommand,
    BotCommandScopeChat,
    BotCommandScopeDefault,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# 🔑 Токен бота (из переменной окружения)
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("❌ Токен не найден! Убедись, что переменная окружения TOKEN установлена.")

# 🔐 ПАРОЛЬ ДЛЯ ДОСТУПА
# ⚠️ ЗАМЕНИТЕ "CHANGE_ME_2026" НА СВОЙ НОВЫЙ ПАРОЛЬ ПЕРЕД ЗАПУСКОМ!
BOT_PASSWORD = "has_2027"

# 👑 АДМИН(Ы) БОТА — только эти Telegram ID могут вызывать /reset_access и /check_files
# Узнать свой ID: напишите боту @userinfobot в Telegram, он сразу пришлёт число.
# Затем добавьте переменную окружения ADMIN_ID = ваш_id (там же, где TOKEN).
# Если нужно несколько админов — перечислите ID через запятую: ADMIN_ID=111,222
_admin_env = os.getenv("ADMIN_ID", "")
ADMIN_IDS = {int(x.strip()) for x in _admin_env.split(",") if x.strip().isdigit()}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# 📁 Пути к папкам
HW_DIR = "./дз/"
NOTES_DIR = "./конспекты/"

# 📁 Файл для хранения проверенных пользователей
# Если на хостинге настроена постоянная папка (например DATA_DIR=/app/data на bothost.ru),
# храним файл там — иначе список доступа будет обнуляться при каждом передеплое бота.
DATA_DIR = os.getenv("DATA_DIR", ".")
VERIFIED_USERS_FILE = os.path.join(DATA_DIR, "verified_users.json")

# 🔹 Список номеров ДЗ
NUMBERS = list(range(1, 7)) + ["7_изобр", "7_звуки"] + list(range(8, 19)) + ["19_21"] + list(range(22, 28))

# 📜 Полный текст оферты
FULL_OFFER = (
    "<b>❗️ Условия использования бота и услуг Исполнителя (Хасянова Ибрахима Галимовича):❗️</b>\n\n"
    "<b>Договор считается заключённым при нажатии кнопки «Принять оферту»</b>\n\n"
    "<b>ПОРЯДОК ОКАЗАНИЯ:</b>\n"
    "• Запрещено передавать ссылки, записи и учебные материалы третьим лицам без согласия Исполнителя.\n\n"
    "<b>ОПЛАТА:</b>\n"
    "• При просрочке оплаты более 3 дней доступ к занятиям и материалам может быть приостановлен.\n"
    "• Перенести или отменить занятие можно не менее чем за 12 часов до его начала.\n"
    "• Если уведомить позже, занятие считается состоявшимся и оплачивается полностью.\n"
    "• Опоздание ученика более чем на 15 минут приравнивается к состоявшемуся занятию с полной оплатой.\n"
    "• Более двух отмен/переносов подряд дают Исполнителю право требовать 100% предоплату за следующие занятия или изменить условия.\n\n"
    "<b>АВТОРСКИЕ ПРАВА:</b>\n"
    "• Все учебные материалы, записи и программный код бота являются интеллектуальной собственностью Исполнителя. Их коммерческое или публичное использование без письменного согласия запрещено.\n"
    "• Исполнитель вправе изменять условия оферты, новая редакция вступает в силу для будущих платежей.\n\n"
    "🔹 Ознакомьтесь с условиями. Чтобы продолжить, нажмите кнопку ниже — она отправит сообщение о согласии от вашего имени."
)

# 📜 Текст согласия — ученик отправляет его САМ (через reply-кнопку), это его собственное
# сообщение в чате, а не текст от бота. Используется и как подпись кнопки, и для сверки.
OFFER_CONSENT_TEXT = "Я даю полное согласие со всеми условиями оферты Исполнителя (Хасянова Ибрахима Галимовича)."

# 🔹 Номера ДЗ с доп. файлами
HW_WITH_FOLDER = {3, 9, 10, 17, 18, 22, 24}

# 📝 ОТВЕТЫ НА ВСЕ ДЗ
homework = {
    1: ["14", "25", "17", "18", "124", "25", "42", "18", "68", "46"],
    2: ["zwyx", "xzyw", "wxyz", "cdab", "wxyz", "yxzw", "yxwz", "zywx", "xyzw", "zxwy"],
    3: ["60065", "305", "1164", "360480", "8400", "64460", "1985", "723", "941", "241626112"],
    4: ["8", "7", "16", "18", "21", "12", "19", "14", "100", "1010"],
    5: ["20", "9", "11", "69", "11", "17", "35", "8", "29", "1958"],
    6: ["64", "44", "21", "18", "187", "102", "34", "40", "374", "72"],
    "7_изобр": ["512", "512", "229", "206550", "658", "295425", "32", "128", "62301", "16"],
    "7_звуки": ["17", "43200", "10", "15", "44", "320", "124", "3200", "2", "12"],
    8: ["840", "117601", "3352", "239760", "7466", "46656", "2430", "144", "588", "1610507"],
    9: ["261", "3", "94", "2", "46", "3", "13412", "112", "75", "53"],
    10: ["47", "42", "10", "7", "5", "6", "2", "117", "20", "8"],
    11: ["512", "256", "12", "22", "896", "7", "200", "129", "8", "9"],
    12: ["28", "701", "622", "120", "239", "544", "618", "254", "442", "126"],
    13: ["14", "254", "2", "15", "34160160", "2", "192", "1195255254", "349526", "378"],
    14: ["43", "15", "220", "2029", "26", "5718", "27", "250", "224", "224"],
    15: ["89", "25", "17", "54", "54", "78", "19", "41", "3", "190"],
    16: ["12114", "4045", "8102", "77309406959", "67", "750", "12487", "1078", "66048", "38043606640000"],
    17: ["1591 9233", "2089 99343", "720 87094", "2890 276074548",
         "8631 199187", "99999 1985089", "2627 504410", "104 191",
         "249933", "77 8664"],
    18: ["2071 649", "2292 524", "2407 1101", "2662 364",
         "2400 852", "2538 630", "2671 419", "1271 754",
         "2358 877", "3154 887"],
    "19_21": ["27 24 26 23", "118 113 117 112", "45 40 44 39 43", "8 7 20 19",
              "28 48 54 47", "17 11 23 6", "13 10 19 6", "28 25 52 33",
              "40 10 39 7", "54 98 106 97"],
    22: ["1375", "36", "14", "6", "18", "32", "3", "7", "7", "158"],
    23: ["133", "200", "200", "133280", "12", "301", "22", "273", "6090", "12420"],
    24: ["544", "202", "22", "19", "169", "750", "111", "2981", "154", "35"],
    25: [
        "1253475 619\n12103425 5977\n12593475 6219\n12913425 6377",
        "800001 309\n800003 47059\n800004 409\n800006 269\n800007 39\n800009 4969",
        "12056537 38767\n12153569 39079\n12451507 40037\n12459593 40063\n12655523 40693\n12854563 41333",
        "113190511 437029\n133133511 514029\n163177511 630029\n183120511 707029",
        "700004 350004\n700009 41194\n700023 233344\n700024 350014\n700044 350024",
        "71723432 33784\n74483332 35084\n77243232 36384\n79153932 37284",
        "3 58153\n7 24923\n59 2957\n13 13421\n149 1171\n5 34897\n211 827\n2 87251",
        "6593785 1187\n60143985 10827\n61143885 11007\n62143785 11187\n63143685 11367\n64143585 11547\n65143485 11727\n66143385 11907\n67143285 12087\n68143185 12267\n69143085 12447",
        "142 473759\n118 462767\n126 464999\n118 461969\n118 477071",
        "6080069\n6080131\n6080141\n6080147\n6080149\n6080153\n6080161"
    ],
    26: ["?", "?", "?", "?", "?", "?", "?", "?", "?", "?"],
    27: ["?", "?", "?", "?", "?", "?", "?", "?", "?", "?"],
}

# 📊 Состояния пользователей
user_checking = {}

# 📜 Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# 🔧 Нормализация ответа
def normalize(s: str) -> str:
    return " ".join(s.lower().split())


# 🔧 ИСПРАВЛЕНИЕ БАГА: в Python 3.6+ int("19_21") = 1921 (подчёркивание — разделитель!)
_SPECIAL_HW_KEYS = {
    "19_21": "19_21",
    "1921":  "19_21",
    "7_изобр": "7_изобр",
    "7_звуки": "7_звуки",
}


def parse_hw_key(s: str):
    if s in _SPECIAL_HW_KEYS:
        return _SPECIAL_HW_KEYS[s]
    try:
        return int(s)
    except ValueError:
        return s


def normalize_hw_key(hw_num):
    if hw_num in _SPECIAL_HW_KEYS or str(hw_num) in _SPECIAL_HW_KEYS:
        return _SPECIAL_HW_KEYS.get(hw_num) or _SPECIAL_HW_KEYS.get(str(hw_num))
    return hw_num


def get_base_filename(num) -> str:
    """
    Единая логика построения 'базового' имени файла для номера ДЗ/конспекта.
    Используется и при отправке файла, и при диагностике (/check_files),
    чтобы они никогда не разъезжались между собой.
    """
    if str(num) in ["19", "20", "21", "19_21", "1921"]:
        return "19_21"
    if str(num) == "7_изобр":
        return "7_изобр"
    if str(num) == "7_звуки":
        return "7_звуки"
    return str(num)


# 🔎 Устойчивый поиск файла (защита от unicode NFC/NFD рассинхрона в кириллических именах,
# который часто возникает, если файлы хоть раз проходили через macOS/архиватор)
def find_file_robust(directory: str, filename: str):
    direct_path = os.path.join(directory, filename)
    if os.path.exists(direct_path):
        return direct_path
    if not os.path.isdir(directory):
        return None
    target = unicodedata.normalize("NFC", filename).lower()
    try:
        entries = os.listdir(directory)
    except OSError:
        return None
    for entry in entries:
        if unicodedata.normalize("NFC", entry).lower() == target:
            return os.path.join(directory, entry)
    return None


# 💾 Работа с проверенными пользователями
# Формат: {user_id: {"name": ..., "username": ..., "verified_at": ...}}
# (раньше был просто список ID — старый формат подхватывается автоматически)
def load_verified_users():
    if os.path.exists(VERIFIED_USERS_FILE):
        try:
            with open(VERIFIED_USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                # старый формат — просто список ID, без имён
                return {int(uid): {"name": "", "username": "", "verified_at": ""} for uid in data}
            return {int(uid): info for uid, info in data.items()}
        except (json.JSONDecodeError, ValueError, AttributeError):
            return {}
    return {}


def save_verified_users(verified_dict):
    try:
        os.makedirs(os.path.dirname(VERIFIED_USERS_FILE) or ".", exist_ok=True)
        with open(VERIFIED_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({str(uid): info for uid, info in verified_dict.items()}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка при сохранении проверенных пользователей: {e}")


# 🚫 Чёрный список — отдельно от verified_users.
# Сюда попадают через /revoke те, у кого расторгнут договор: даже зная общий пароль класса,
# они больше не смогут зайти, пока админ явно не вернёт доступ через /grant.
BANNED_USERS_FILE = os.path.join(DATA_DIR, "banned_users.json")


def load_banned_users():
    if os.path.exists(BANNED_USERS_FILE):
        try:
            with open(BANNED_USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {int(uid): info for uid, info in data.items()}
        except (json.JSONDecodeError, ValueError, AttributeError):
            return {}
    return {}


def save_banned_users(banned_dict):
    try:
        os.makedirs(os.path.dirname(BANNED_USERS_FILE) or ".", exist_ok=True)
        with open(BANNED_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({str(uid): info for uid, info in banned_dict.items()}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка при сохранении чёрного списка: {e}")


# 🌍 Глобальное множество проверенных пользователей
verified_users = load_verified_users()
banned_users = load_banned_users()


# 🛡️ ДЕКОРАТОР ДОСТУПА
# Вешается на любой обработчик, который должен работать ТОЛЬКО для проверенных пользователей.
# Проверяет verified_users заново при КАЖДОМ нажатии/сообщении — а не один раз при /start.
# Поэтому отзыв доступа (через /reset_access) мгновенно блокирует уже открытые меню у учеников.
def require_verified(handler):
    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id in verified_users:
            return await handler(update, context)

        # Доступа нет — сбрасываем любое незавершённое состояние и сообщаем об этом
        user_checking.pop(user_id, None)
        denial_text = (
            "⛔ Ваш доступ к боту закрыт.\n"
            "Если вы новый ученик — нажмите /start и введите пароль, выданный преподавателем."
        )
        if update.callback_query:
            query = update.callback_query
            await query.answer("⛔ Доступ закрыт", show_alert=True)
            try:
                await query.edit_message_text(denial_text)
            except Exception:
                pass
        elif update.message:
            await update.message.reply_text(denial_text)
        return
    return wrapper


# 🔁 Показать кнопки с ошибками для повтора
async def show_retry_keyboard(message, hw_key, results):
    wrong_tasks = [i + 1 for i, ok in enumerate(results) if not ok]
    if not wrong_tasks:
        return False
    keyboard = []
    row = []
    for t_num in wrong_tasks:
        row.append(InlineKeyboardButton(
            f"❌ №{t_num}",
            callback_data=f"retry_{hw_key}_{t_num}"
        ))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_main")])
    await message.reply_text(
        "🔁 Хочешь переделать конкретное задание? Нажми на номер:",
        reply_markup=InlineKeyboardMarkup(keyboard),

    )
    return True


# 🔗 Полезные ссылки
@require_verified
async def on_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channel_link = "https://t.me/hasyanov_EGE"
    bot_link = "https://t.me/hasyanov_bot"
    contact = "@hassyanov"
    text = (
        "📌 Вот полезные ссылки:\n\n"
        f"📢 <b>ТГ-канал</b>: {channel_link}\n"
        f"🤖 <b>Этот бот</b>: {bot_link}\n"
        f"📩 <b>Мой контакт</b>: {contact}"
    )
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# 📥 Отправка PDF (по уже готовому пути)
async def send_pdf(query, file_path: str, caption: str = ""):
    try:
        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                await query.message.reply_document(document=f, caption=caption, protect_content=True)
            return True
        else:
            await query.message.reply_text(
                f"❌ Файл не найден: `{file_path}`", parse_mode="Markdown"
            )
            return False
    except Exception as e:
        logger.error(f"Ошибка при отправке PDF: {e}")
        await query.message.reply_text(f"❌ Ошибка при отправке файла: {e}")
        return False


# 📥 Отправка ДЗ + доп. файлы
async def send_hw_pdf(query, hw_num):
    main_filename = get_base_filename(hw_num)

    # ⬇️ ключевое изменение: ищем файл устойчиво к unicode-несовпадениям,
    # а не просто строим путь и надеемся, что он совпадёт побайтово
    main_path = find_file_robust(HW_DIR, f"дз_{main_filename}.pdf")
    if main_path is None:
        main_path = os.path.join(HW_DIR, f"дз_{main_filename}.pdf")  # для текста ошибки

    if await send_pdf(query, main_path, f"📚 ДЗ №{hw_num}"):
        zip_path = find_file_robust(HW_DIR, f"файлы_{hw_num}.zip")
        if zip_path:
            try:
                with open(zip_path, "rb") as f:
                    await query.message.reply_document(
                        document=f, caption="📦 Дополнительные файлы (ZIP)", protect_content=True
                    )
            except Exception as e:
                await query.message.reply_text(f"⚠️ Не удалось отправить ZIP: {e}")
            return

        if isinstance(hw_num, int) and hw_num in HW_WITH_FOLDER:
            folder_path = os.path.join(HW_DIR, f"файлы_{hw_num}")
            if os.path.exists(folder_path) and os.path.isdir(folder_path):
                files = sorted(
                    os.listdir(folder_path),
                    key=lambda x: (
                        int(x.split('_')[1].split('.')[0])
                        if '_' in x and x.split('_')[1].split('.')[0].isdigit()
                        else 0
                    )
                )
                for filename in files:
                    file_path = os.path.join(folder_path, filename)
                    if os.path.isfile(file_path):
                        try:
                            with open(file_path, "rb") as f:
                                await query.message.reply_document(
                                    document=f, caption=f"📎 {filename}", protect_content=True
                                )
                        except Exception as e:
                            await query.message.reply_text(
                                f"⚠️ Не удалось отправить {filename}: {e}"
                            )


# 📖 Конспект
async def send_note_pdf(query, note_num):
    filename = get_base_filename(note_num)
    note_path = find_file_robust(NOTES_DIR, f"Конспект_{filename}.pdf")
    if note_path is None:
        note_path = os.path.join(NOTES_DIR, f"Конспект_{filename}.pdf")
    await send_pdf(query, note_path, f"📝 Конспект №{filename}")


# 🏁 Главное меню
async def show_main_menu(chat_id, context: ContextTypes.DEFAULT_TYPE,
                         message_text: str = "👋 Чем займёмся сегодня?"):
    keyboard = [
        [InlineKeyboardButton("📚 Получить ДЗ", callback_data="action_get")],
        [InlineKeyboardButton("🔍 Проверить ДЗ", callback_data="action_check")],
        [InlineKeyboardButton("📝 Конспекты", callback_data="action_notes")],
        [InlineKeyboardButton("🔗 Полезные ссылки", callback_data="action_links")],
    ]
    await context.bot.send_message(
        chat_id=chat_id,
        text=message_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# 🏁 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in verified_users:
        context.user_data["agreed"] = True
        context.user_data["password_verified"] = True
        # Подтягиваем актуальное имя/username — полезно после /grant (когда они ещё не были известны)
        # и на случай, если ученик сменил имя в Telegram.
        user = update.effective_user
        entry = verified_users[user_id]
        if entry.get("name") != (user.full_name or "") or entry.get("username") != (user.username or ""):
            entry["name"] = user.full_name or ""
            entry["username"] = user.username or ""
            save_verified_users(verified_users)
        await show_main_menu(update.effective_chat.id, context)
        return
    if user_id in banned_users:
        await update.message.reply_text(
            "🚫 Доступ для вас закрыт администратором. Обратитесь к преподавателю напрямую.",

        )
        return
    if context.user_data.get("agreed", False) and not context.user_data.get("password_verified", False):
        await update.message.reply_text("🔐 Введите пароль, полученный от преподавателя:")
        return
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton(OFFER_CONSENT_TEXT)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await update.message.reply_text(
        FULL_OFFER, reply_markup=keyboard, parse_mode="HTML"
    )


# 🎛️ Выбор действия
@require_verified
async def on_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = []
    for i in range(0, len(NUMBERS), 3):
        row = [
            InlineKeyboardButton(str(num), callback_data=f"{query.data}_{num}")
            for num in NUMBERS[i:i+3]
        ]
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])
    text = "Выбери:"
    if query.data == "action_get":
        text = "📚 Какое ДЗ нужно?"
    elif query.data == "action_check":
        text = "🔍 Какое ДЗ проверим?"
    elif query.data == "action_notes":
        text = "📝 Какой конспект нужен?"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# 📥 Получить ДЗ
@require_verified
async def on_get_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("action_get_"):
        hw_num_str = query.data[len("action_get_"):]
        hw_num = parse_hw_key(hw_num_str)
        await send_hw_pdf(query, hw_num)
        await show_main_menu(query.message.chat_id, context, f"📚 ДЗ №{hw_num_str} отправлено! Что дальше?")


# 📖 Конспекты
@require_verified
async def on_note_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("action_notes_"):
        note_num_str = query.data[len("action_notes_"):]
        note_num = parse_hw_key(note_num_str)
        await send_note_pdf(query, note_num)
        await show_main_menu(query.message.chat_id, context, f"📝 Конспект №{note_num_str} отправлен! Что дальше?")


# 🔍 Проверить ДЗ — выбор номера ДЗ → показываем выбор задания
@require_verified
async def on_check_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not query.data.startswith("action_check_"):
        return

    hw_num_str = query.data[len("action_check_"):]
    hw_key = parse_hw_key(hw_num_str)

    total = len(homework.get(hw_key, []))
    if total == 0:
        await query.edit_message_text(f"❌ ДЗ №{hw_num_str} не найдено в базе.")
        return

    keyboard = []
    keyboard.append([InlineKeyboardButton("📋 Все по порядку (с №1)", callback_data=f"chktask_{hw_key}_all")])

    row = []
    for t_num in range(1, total + 1):
        row.append(InlineKeyboardButton(str(t_num), callback_data=f"chktask_{hw_key}_{t_num}"))
        if len(row) == 5:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")])

    await query.edit_message_text(
        f"🔍 ДЗ №{hw_num_str} — выбери с какого задания начать:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# 🆕 Выбор конкретного задания для начала проверки
@require_verified
async def on_check_task_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    without_prefix = query.data[len("chktask_"):]
    last_underscore = without_prefix.rfind("_")
    if last_underscore == -1:
        return

    hw_key_str = without_prefix[:last_underscore]
    task_num_str = without_prefix[last_underscore + 1:]

    hw_key = parse_hw_key(hw_key_str)

    total = len(homework.get(hw_key, []))
    if total == 0:
        await query.edit_message_text(f"❌ ДЗ не найдено в базе (ключ: {hw_key_str}).")
        return

    if task_num_str == "all":
        start_task = 1
        mode_single = False
    else:
        try:
            start_task = int(task_num_str)
        except ValueError:
            await query.edit_message_text("❌ Ошибка: неверный номер задания.")
            return
        mode_single = True

    user_id = query.from_user.id
    user_checking[user_id] = {
        "hw": hw_key,
        "task": start_task,
        "results": [False] * total,
        "answered": set(),
        "single_task": mode_single,
        "single_task_num": start_task if mode_single else None,
    }

    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_check")]]
    if mode_single:
        await query.edit_message_text(
            f"🔍 ДЗ №{hw_key_str}\n📌 Задание #{start_task} из {total}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.edit_message_text(
            f"✅ Проверим ДЗ №{hw_key_str}\n📌 Задание #1 из {total}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# 🔁 Повтор конкретного задания по кнопке (после итога)
@require_verified
async def on_retry_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    without_prefix = query.data[len("retry_"):]
    last_underscore = without_prefix.rfind("_")
    if last_underscore == -1:
        return

    hw_key_str = without_prefix[:last_underscore]
    task_num_str = without_prefix[last_underscore + 1:]

    hw_key = parse_hw_key(hw_key_str)

    try:
        task_num = int(task_num_str)
    except ValueError:
        await query.edit_message_text("❌ Ошибка: неверный номер задания.")
        return

    user_id = query.from_user.id
    total = len(homework.get(hw_key, []))

    if user_id not in user_checking:
        user_checking[user_id] = {
            "hw": hw_key,
            "task": task_num,
            "results": [False] * total,
            "answered": set(),
            "retry_mode": True,
        }
    else:
        user_checking[user_id]["task"] = task_num
        user_checking[user_id]["retry_mode"] = True

    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_check")]]
    await query.edit_message_text(
        f"📌 Введи ответ на задание #{task_num} (ДЗ №{hw_key_str}):",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ✍️ Ввод ответа на ДЗ
@require_verified
async def on_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_checking.get(user_id)
    if not state:
        return

    hw_num = state["hw"]
    task_num = state["task"]
    user_input = update.message.text.strip()

    hw_key = normalize_hw_key(hw_num)

    if hw_key not in homework:
        await update.message.reply_text(f"❌ ДЗ №{hw_key} не найдено в базе")
        del user_checking[user_id]
        return

    correct_answers = homework[hw_key]
    total = len(correct_answers)

    if task_num < 1 or task_num > total:
        await update.message.reply_text(f"❌ Задание №{task_num} не найдено")
        return

    correct_ans = str(correct_answers[task_num - 1]).strip()
    is_correct = normalize(user_input) == normalize(correct_ans)

    if is_correct:
        await update.message.reply_text("✅ Верно!")
    else:
        await update.message.reply_text("❌ Неверно.")

    idx = task_num - 1
    if idx < len(state["results"]):
        state["results"][idx] = is_correct
    if "answered" not in state:
        state["answered"] = set()
    state["answered"].add(task_num)

    # ── РЕЖИМ RETRY ───────────────────────────────────────────────────────────
    if state.get("retry_mode"):
        state.pop("retry_mode", None)
        results = state["results"]
        correct_count = sum(results)
        await update.message.reply_text(f"📊 Текущий результат по ДЗ №{hw_key}: {correct_count}/{total}")
        has_errors = await show_retry_keyboard(update.message, hw_key, results)
        if not has_errors:
            del user_checking[user_id]
            await show_main_menu(update.effective_chat.id, context, "🎉 Все задания верны! Что дальше?")
        return

    # ── РЕЖИМ ОДНОГО ЗАДАНИЯ ──────────────────────────────────────────────────
    if state.get("single_task"):
        del user_checking[user_id]
        keyboard = [
            [InlineKeyboardButton("🔍 Проверить ещё задание", callback_data="action_check")],
            [InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_main")],
        ]
        await update.message.reply_text(
            "Хочешь проверить ещё одно задание или вернуться в меню?",
            reply_markup=InlineKeyboardMarkup(keyboard),

        )
        return

    # ── ОБЫЧНЫЙ РЕЖИМ (все по порядку) ────────────────────────────────────────
    next_task = task_num + 1
    if next_task <= total:
        state["task"] = next_task
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_check")]]
        await update.message.reply_text(
            f"📌 Задание #{next_task} из {total}:",
            reply_markup=InlineKeyboardMarkup(keyboard),

        )
    else:
        results = state["results"]
        correct_count = sum(results)
        phrase = "Ты молодец!" if correct_count == total else "Тренируйся. Есть ошибки."
        summary = f"✅ ДЗ_{hw_key} решено: {correct_count}/{total}\n«{phrase}»"
        await update.message.reply_text(summary)
        await update.message.reply_text(
            "📸 Сделай скриншот этого результата и отправь мне его в личку!\nЯ оценю твой прогресс 😊",

        )

        has_errors = await show_retry_keyboard(update.message, hw_key, results)
        if not has_errors:
            del user_checking[user_id]
            await show_main_menu(update.effective_chat.id, context, "🎉 Проверка завершена! Что дальше?")


# ✍️ Проверка пароля
async def on_password_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    if user_id in verified_users:
        return
    if user_id in banned_users:
        await update.message.reply_text(
            "🚫 Доступ для вас закрыт администратором. Обратитесь к преподавателю напрямую.",

        )
        return

    # ── Согласие с офертой: это реальное сообщение, отправленное самим учеником ────────
    if message_text == OFFER_CONSENT_TEXT and not context.user_data.get("agreed", False):
        context.user_data["agreed"] = True
        context.user_data["password_verified"] = False
        await update.message.reply_text(
            "🔐 Введите пароль, полученный от преподавателя:",
            reply_markup=ReplyKeyboardRemove(),

        )
        return

    if not context.user_data.get("agreed", False) or context.user_data.get("password_verified", False):
        return
    if message_text == BOT_PASSWORD:
        context.user_data["password_verified"] = True
        user = update.effective_user
        verified_users[user_id] = {
            "name": user.full_name or "",
            "username": user.username or "",
            "verified_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        save_verified_users(verified_users)
        await update.message.reply_text("✅ Пароль верен! Добро пожаловать!")
        await show_main_menu(update.effective_chat.id, context)
    else:
        await update.message.reply_text(
            "❌ Неверный пароль! Попробуйте ещё раз или обратитесь к преподавателю.",

        )


# ❌ Отмена ввода пароля
async def on_cancel_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["waiting_for_password"] = False
    await query.edit_message_text(
        "Ввод пароля отменён.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_main")]]
        )
    )


# 🔄 Назад / Отмена
@require_verified
async def on_back_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id in user_checking:
        del user_checking[user_id]
    if query.data == "back_to_main":
        await show_main_menu(query.message.chat_id, context, "Главное меню:")
    elif query.data == "cancel_check":
        await show_main_menu(query.message.chat_id, context, "Проверка отменена!")


# 👑 /reset_access — мгновенно отозвать доступ у ВСЕХ учеников (только для админа)
async def reset_access(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not ADMIN_IDS:
        await update.message.reply_text(
            "⚠️ ADMIN_ID не настроен в переменных окружения — команда временно недоступна никому.\n"
            "Узнайте свой Telegram ID через @userinfobot и добавьте переменную окружения ADMIN_ID."
        )
        return
    if not is_admin(user_id):
        return  # молчим — не подтверждаем посторонним, что команда вообще существует

    count = len(verified_users)
    verified_users.clear()
    save_verified_users(verified_users)
    user_checking.clear()

    # На всякий случай сбрасываем устаревшие флаги agreed/password_verified у всех,
    # кого бот помнит в памяти (защита уже обеспечена декоратором require_verified,
    # но так интерфейс /start ведёт себя предсказуемо сразу для всех).
    try:
        for uid, udata in context.application.user_data.items():
            udata["agreed"] = False
            udata["password_verified"] = False
    except Exception as e:
        logger.error(f"Не удалось сбросить user_data: {e}")

    await update.message.reply_text(
        f"✅ Доступ отозван у всех учеников ({count} чел.).\n"
        "Не забудьте также сменить BOT_PASSWORD в коде на новый перед началом следующего потока."
    )


# 👑 /check_files — найти отсутствующие/неправильно названные файлы (только для админа)
async def check_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    missing_hw = []
    renamed_hw = []
    for num in NUMBERS:
        base = get_base_filename(num)
        expected = f"дз_{base}.pdf"
        direct = os.path.join(HW_DIR, expected)
        if os.path.exists(direct):
            continue
        found = find_file_robust(HW_DIR, expected)
        if found:
            renamed_hw.append(f"№{num}: ожидался «{expected}», найден «{os.path.basename(found)}» (несовпадение unicode-формы — переименуйте файл)")
        else:
            missing_hw.append(f"№{num}: {expected}")

    missing_notes = []
    renamed_notes = []
    for num in NUMBERS:
        base = get_base_filename(num)
        expected = f"Конспект_{base}.pdf"
        direct = os.path.join(NOTES_DIR, expected)
        if os.path.exists(direct):
            continue
        found = find_file_robust(NOTES_DIR, expected)
        if found:
            renamed_notes.append(f"№{num}: ожидался «{expected}», найден «{os.path.basename(found)}»")
        else:
            missing_notes.append(f"№{num}: {expected}")

    lines = ["📋 <b>Диагностика файлов</b>\n"]

    if not os.path.isdir(HW_DIR):
        lines.append(f"❌ Папка ДЗ не найдена вообще: {HW_DIR}")
    elif missing_hw:
        lines.append(f"❌ <b>Отсутствуют ДЗ ({len(missing_hw)}):</b>")
        lines.extend(missing_hw)
    else:
        lines.append("✅ Все ДЗ-файлы на месте.")

    if renamed_hw:
        lines.append("\n⚠️ <b>ДЗ найдены, но с другим именем (unicode):</b>")
        lines.extend(renamed_hw)

    lines.append("")

    if not os.path.isdir(NOTES_DIR):
        lines.append(f"❌ Папка конспектов не найдена вообще: {NOTES_DIR}")
    elif missing_notes:
        lines.append(f"❌ <b>Отсутствуют конспекты ({len(missing_notes)}):</b>")
        lines.extend(missing_notes)
    else:
        lines.append("✅ Все конспекты на месте.")

    if renamed_notes:
        lines.append("\n⚠️ <b>Конспекты найдены, но с другим именем (unicode):</b>")
        lines.extend(renamed_notes)

    text = "\n".join(lines)
    # Telegram ограничивает сообщение ~4096 символами — на всякий случай режем
    for chunk_start in range(0, len(text), 3500):
        await update.message.reply_text(text[chunk_start:chunk_start + 3500], parse_mode="HTML")


# 👑 /students — список учеников с доступом (только для админа)
async def list_students(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    students = {uid: info for uid, info in verified_users.items() if uid not in ADMIN_IDS}

    if not students:
        await update.message.reply_text("📋 Сейчас нет ни одного ученика с доступом.")
        return

    lines = [f"📋 <b>Учеников с доступом: {len(students)}</b>\n"]
    for uid, info in students.items():
        name = info.get("name") or "Без имени"
        username = f" (@{info['username']})" if info.get("username") else ""
        when = info.get("verified_at")
        when_str = f" — вошёл {when}" if when else ""
        lines.append(f"• {name}{username} — id <code>{uid}</code>{when_str}")

    text = "\n".join(lines)
    for chunk_start in range(0, len(text), 3500):
        await update.message.reply_text(text[chunk_start:chunk_start + 3500], parse_mode="HTML")


# 👑 /revoke <id> — забрать доступ у ОДНОГО ученика, не трогая остальных (только для админа)
async def revoke_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    if not context.args:
        await update.message.reply_text(
            "Использование: <code>/revoke ID</code>\nID ученика можно посмотреть командой /students",
            parse_mode="HTML"
        )
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID должен быть числом — посмотри его через /students.")
        return

    if target_id not in verified_users:
        await update.message.reply_text(f"⚠️ У пользователя {target_id} и так нет доступа.")
        return

    info = verified_users.pop(target_id)
    save_verified_users(verified_users)
    user_checking.pop(target_id, None)

    banned_users[target_id] = {
        "name": info.get("name") or "",
        "username": info.get("username") or "",
        "revoked_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    save_banned_users(banned_users)

    name = info.get("name") or str(target_id)
    await update.message.reply_text(
        f"✅ Доступ у «{name}» (id {target_id}) отозван навсегда.\n"
        f"Даже зная пароль, он больше не сможет войти — пока ты не вернёшь доступ через /grant {target_id}."
    )


# 👑 /broadcast текст — разослать сообщение всем ученикам с доступом (только для админа)
async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    if not context.args:
        await update.message.reply_text("Использование: <code>/broadcast текст сообщения</code>", parse_mode="HTML")
        return

    text = " ".join(context.args)
    sent, failed = 0, 0
    for uid in list(verified_users.keys()):
        try:
            await context.bot.send_message(chat_id=uid, text=f"📢 {text}")
            sent += 1
        except Exception as e:
            failed += 1
            logger.error(f"Не удалось отправить рассылку пользователю {uid}: {e}")

    await update.message.reply_text(f"✅ Рассылка отправлена: {sent} получили, {failed} не удалось доставить.")


# 👑 /grant <id> — вернуть доступ конкретному ID напрямую: снимает с чёрного списка
# и сразу даёт доступ, без повторного ввода пароля (только для админа)
async def grant_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    if not context.args:
        await update.message.reply_text(
            "Использование: <code>/grant ID</code>\nID можно узнать через /students или попросив ученика написать @userinfobot",
            parse_mode="HTML"
        )
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID должен быть числом.")
        return

    was_banned = banned_users.pop(target_id, None)
    if was_banned:
        save_banned_users(banned_users)

    if target_id in verified_users:
        await update.message.reply_text(f"⚠️ У {target_id} и так есть доступ.")
        return

    verified_users[target_id] = {
        "name": (was_banned or {}).get("name", ""),
        "username": (was_banned or {}).get("username", ""),
        "verified_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    save_verified_users(verified_users)

    await update.message.reply_text(
        f"✅ Доступ выдан напрямую (id {target_id}), пароль не понадобился.\n"
        f"Имя обновится автоматически, как только ученик откроет бота командой /start."
    )


# 👑 Команды-подсказки только в личном чате с админом (у остальных виден только /start)
async def post_init(application: Application):
    await application.bot.set_my_commands(
        [BotCommand("start", "Начать работу с ботом")],
        scope=BotCommandScopeDefault()
    )
    admin_commands = [
        BotCommand("students", "Список учеников с доступом"),
        BotCommand("revoke", "Забрать доступ у одного ученика по ID (навсегда)"),
        BotCommand("grant", "Вернуть/выдать доступ ученику по ID"),
        BotCommand("reset_access", "Отозвать доступ у ВСЕХ учеников"),
        BotCommand("broadcast", "Разослать сообщение всем ученикам"),
        BotCommand("check_files", "Проверить наличие файлов ДЗ/конспектов"),
    ]
    for admin_id in ADMIN_IDS:
        try:
            await application.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            logger.error(f"Не удалось установить команды для админа {admin_id}: {e}")


# 🚀 Запуск
def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset_access", reset_access))
    app.add_handler(CommandHandler("check_files", check_files))
    app.add_handler(CommandHandler("students", list_students))
    app.add_handler(CommandHandler("revoke", revoke_student))
    app.add_handler(CommandHandler("grant", grant_student))
    app.add_handler(CommandHandler("broadcast", broadcast_message))
    app.add_handler(CallbackQueryHandler(on_action, pattern="^action_(get|check|notes)$"))
    app.add_handler(CallbackQueryHandler(on_links, pattern="^action_links$"))
    app.add_handler(CallbackQueryHandler(on_get_selected, pattern="^action_get_"))
    app.add_handler(CallbackQueryHandler(on_check_selected, pattern="^action_check_"))
    app.add_handler(CallbackQueryHandler(on_note_selected, pattern="^action_notes_"))
    app.add_handler(CallbackQueryHandler(on_check_task_start, pattern=r"^chktask_"))
    app.add_handler(CallbackQueryHandler(on_retry_task, pattern=r"^retry_"))
    app.add_handler(CallbackQueryHandler(on_back_button, pattern="^(back_to_main|cancel_check)$"))
    app.add_handler(CallbackQueryHandler(on_cancel_password, pattern="^cancel_password$"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_password_input), group=0)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_answer), group=1)

    print("✅ Бот запущен с защитой!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
