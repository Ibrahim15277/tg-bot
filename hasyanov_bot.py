import logging
import os
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
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

# 🔐 ПАРОЛЬ ДЛЯ ДОСТУПА (ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ!)
BOT_PASSWORD = "student_has"  # ← ЗАМЕНИТЕ НА СВОЙ!

# 📁 Пути к папкам
HW_DIR = "./дз/"
NOTES_DIR = "./конспекты/"

# 📁 Файл для хранения ID проверенных пользователей
VERIFIED_USERS_FILE = "verified_users.json"

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
    "🔹 Ознакомьтесь с условиями. Для продолжения необходимо принять оферту."
)

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
    12: ["?", "?", "?", "?", "?", "?", "?", "?", "?", "?"],
    13: ["14", "254", "2", "15", "34160160", "2", "192", "1195255254", "349526", "378"],
    14: ["43","15", "220", "2029", "26", "5718", "27", "250", "224", "224"],
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

# 💾 Функции для работы с проверенными пользователями
def load_verified_users():
    if os.path.exists(VERIFIED_USERS_FILE):
        try:
            with open(VERIFIED_USERS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_verified_users(verified_set):
    try:
        with open(VERIFIED_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(verified_set), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка при сохранении проверенных пользователей: {e}")

# 🌍 Глобальное множество проверенных пользователей
verified_users = load_verified_users()

# 🔗 Полезные ссылки
async def on_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    channel_link = "https://t.me/hasyanov_EGE"
    bot_link = "https://t.me/hasyanov_bot"
    contact = "@ibrahimchiik"
    text = (
        "📌 Вот полезные ссылки:\n\n"
        f"📢 <b>ТГ-канал</b>: {channel_link}\n"
        f"🤖 <b>Этот бот</b>: {bot_link}\n"
        f"📩 <b>Мой контакт</b>: {contact}"
    )
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
    # ❗️ УБРАЛ protect_content — edit_message_text не поддерживает этот параметр!
    await query.edit_message_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

# 📥 Отправка PDF
async def send_pdf(query, file_path: str, caption: str = ""):
    try:
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                await query.message.reply_document(
                    document=f, 
                    caption=caption,
                    protect_content=True  # ✅ Здесь можно — это reply_document
                )
                return True
        else:
            await query.message.reply_text(
                f"❌ Файл не найден: `{file_path}`", 
                parse_mode="Markdown",
                protect_content=True  # ✅ Здесь можно — это reply_text
            )
            return False
    except Exception as e:
        logger.error(f"Ошибка при отправке PDF: {e}")
        await query.message.reply_text(
            f"❌ Ошибка при отправке файла: {e}",
            protect_content=True
        )
        return False

# 📥 Отправка ДЗ + доп. файлы
async def send_hw_pdf(query, hw_num: int | str):
    if str(hw_num) in ["19", "20", "21", "19_21", "1921"]:
        main_filename = "19_21"
    elif str(hw_num) == "7_изобр":
        main_filename = "7_изобр"
    elif str(hw_num) == "7_звуки":
        main_filename = "7_звуки"
    else:
        main_filename = str(hw_num)
    
    main_path = os.path.join(HW_DIR, f"дз_{main_filename}.pdf")
    if await send_pdf(query, main_path, f"📚 ДЗ №{hw_num}"):
        # 🔥 Проверяем ZIP файл
        zip_path = os.path.join(HW_DIR, f"файлы_{hw_num}.zip")
        if os.path.exists(zip_path):
            try:
                with open(zip_path, "rb") as f:
                    await query.message.reply_document(
                        document=f,
                        caption=f"📦 Дополнительные файлы (ZIP)",
                        protect_content=True
                    )
            except Exception as e:
                await query.message.reply_text(
                    f"⚠️ Не удалось отправить ZIP: {e}",
                    protect_content=True
                )
            return  # ✅ Выходим, чтобы не искать папку
        
        # Если ZIP нет, ищем папку (старая логика)
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
                                    document=f,
                                    caption=f"📎 {filename}",
                                    protect_content=True
                                )
                        except Exception as e:
                            await query.message.reply_text(
                                f"⚠️ Не удалось отправить {filename}: {e}",
                                protect_content=True
                            )
# 📖 Конспект
async def send_note_pdf(query, note_num: int | str):
    if str(note_num) in ["19", "20", "21", "19_21", "1921"]:
        filename = "19_21"
    else:
        filename = str(note_num)
    note_path = os.path.join(NOTES_DIR, f"Конспект_{filename}.pdf")
    await send_pdf(query, note_path, f"📝 Конспект №{filename}")

# 🏁 Главное меню
async def show_main_menu(chat_id, context: ContextTypes.DEFAULT_TYPE, 
                        message_text: str = "👋 Чем займёмся сегодня?", 
                        protect: bool = True):
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
        protect_content=protect  # ✅ Здесь можно — это send_message
    )

# 🏁 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # ✅ Если пользователь уже проверен — сразу показываем меню
    if user_id in verified_users:
        context.user_data["agreed"] = True
        context.user_data["password_verified"] = True
        await show_main_menu(update.effective_chat.id, context)
        return
    
    # Если оферта принята, но пароль ещё не введён — ждём текст
    if context.user_data.get("agreed", False) and not context.user_data.get("password_verified", False):
        await update.message.reply_text(
            "🔐 Введите пароль, полученный от преподавателя:",
            protect_content=True
        )
        return

    # Если оферта ещё не принята — показываем её
    keyboard = [[InlineKeyboardButton("✅ Принять оферту", callback_data="accept_offer")]]
    await update.message.reply_text(
        FULL_OFFER,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
        protect_content=True
    )

# 🎛️ Выбор действия
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
    # ❗️ УБРАЛ protect_content — edit_message_text не поддерживает!
    await query.edit_message_text(
        text, 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# 📥 Получить ДЗ
async def on_get_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("action_get_"):
        hw_num_str = query.data[len("action_get_"):]
        try:
            hw_num = int(hw_num_str)
        except ValueError:
            hw_num = hw_num_str
        await send_hw_pdf(query, hw_num)
        await show_main_menu(query.message.chat_id, context, f"📚 ДЗ №{hw_num_str} отправлено! Что дальше?")

# 📖 Конспекты
async def on_note_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("action_notes_"):
        note_num_str = query.data[len("action_notes_"):]
        try:
            note_num = int(note_num_str)
        except ValueError:
            note_num = note_num_str
        await send_note_pdf(query, note_num)
        await show_main_menu(query.message.chat_id, context, f"📝 Конспект №{note_num_str} отправлен! Что дальше?")

# 🔍 Проверить ДЗ
async def on_check_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("action_check_"):
        hw_num_str = query.data[len("action_check_"):]
        if hw_num_str in ["1921", "19_21"]:
            hw_num = "19_21"
        else:
            try:
                hw_num = int(hw_num_str)
            except ValueError:
                hw_num = hw_num_str
        user_id = query.from_user.id
        user_checking[user_id] = {"hw": hw_num, "task": 1}
        keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_check")]]
        # ❗️ УБРАЛ protect_content
        await query.edit_message_text(
            f"✅ Проверим ДЗ №{hw_num_str}\n📌 Задание #1:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ✍️ Ввод ответа на ДЗ
async def on_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = user_checking.get(user_id)
    if not state:
        return
    hw_num = state["hw"]
    task_num = state["task"]
    user_input = update.message.text.strip()
    if isinstance(hw_num, str) and (hw_num == "1921" or hw_num == "19_21"):
        hw_key = "19_21"
    else:
        hw_key = hw_num
    if hw_key not in homework:
        await update.message.reply_text(f"❌ ДЗ №{hw_key} не найдено в базе", protect_content=True)
        return
    correct_answers = homework[hw_key]
    if task_num > len(correct_answers):
        await update.message.reply_text(f"❌ Задание №{task_num} не найдено", protect_content=True)
        return
    correct_ans = str(correct_answers[task_num - 1]).strip()
    def normalize(s: str) -> str:
        parts = s.lower().split()
        return " ".join(parts)
    user_norm = normalize(user_input)
    correct_norm = normalize(correct_ans)
    is_correct = user_norm == correct_norm
    if is_correct:
        await update.message.reply_text("✅ Верно!", protect_content=True)
    else:
        await update.message.reply_text("❌ Неверно.", protect_content=True)
    if "results" not in user_checking[user_id]:
        user_checking[user_id]["results"] = []
    user_checking[user_id]["results"].append(is_correct)
    next_task = task_num + 1
    if next_task <= len(correct_answers):
        user_checking[user_id]["task"] = next_task
        await update.message.reply_text(f"📌 Задание #{next_task}:", protect_content=True)
    else:
        results = user_checking[user_id]["results"]
        correct_count = sum(results)
        total = len(results)
        if correct_count == total:
            phrase = "Ты молодец!"
        else:
            phrase = "Тренеруйся. Есть ошибки."
        summary = f"✅ ДЗ_{hw_key} решено: {correct_count}/{total}\n«{phrase}»"
        await update.message.reply_text(summary, protect_content=True)
        await update.message.reply_text(
            "📤 Скопируй это сообщение и пришли мне в личку!\nЯ проверю твой прогресс 😊",
            protect_content=True
        )
        del user_checking[user_id]
        await show_main_menu(update.effective_chat.id, context, "🎉 Проверка завершена! Что дальше?")

# ✍️ Проверка введённого пароля
async def on_password_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    if user_id in verified_users:
        return
    
    if not context.user_data.get("agreed", False) or context.user_data.get("password_verified", False):
        return
    
    if message_text == BOT_PASSWORD:
        context.user_data["password_verified"] = True
        verified_users.add(user_id)
        save_verified_users(verified_users)
        await update.message.reply_text(
            "✅ Пароль верен! Добро пожаловать!",
            protect_content=True
        )
        await show_main_menu(update.effective_chat.id, context)
    else:
        await update.message.reply_text(
            "❌ Неверный пароль! Попробуйте ещё раз или обратитесь к преподавателю.",
            protect_content=True
        )
        context.user_data["agreed"] = False

# ❌ Отмена ввода пароля (если вдруг нужна)
async def on_cancel_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["waiting_for_password"] = False
    # ❗️ УБРАЛ protect_content
    await query.edit_message_text(
        "Ввод пароля отменён.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 В главное меню", callback_data="back_to_main")]])
    )

# 🔄 Обработчик кнопки "Назад" и "Отмена"
async def on_back_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "back_to_main":
        await show_main_menu(query.message.chat_id, context, "Главное меню:")
    elif query.data == "cancel_check":
        user_id = query.from_user.id
        if user_id in user_checking:
            del user_checking[user_id]
        await show_main_menu(query.message.chat_id, context, "Проверка отменена!")

# ✅ Обработчик принятия оферты
async def on_accept_offer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "Я даю полное согласие со всеми условиями оферты Исполнителя (Хасянова Ибрахима Галимовича).",
        protect_content=True
    )
    context.user_data["agreed"] = True
    await query.message.reply_text(
        "🔐 Введите пароль, полученный от преподавателя:",
        protect_content=True
    )

# 🚀 Запуск
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_accept_offer, pattern="^accept_offer$"))
    app.add_handler(CallbackQueryHandler(on_action, pattern="^action_(get|check|notes)$"))
    app.add_handler(CallbackQueryHandler(on_links, pattern="^action_links$"))
    app.add_handler(CallbackQueryHandler(on_get_selected, pattern="^action_get_"))
    app.add_handler(CallbackQueryHandler(on_check_selected, pattern="^action_check_"))
    app.add_handler(CallbackQueryHandler(on_note_selected, pattern="^action_notes_"))
    app.add_handler(CallbackQueryHandler(on_back_button, pattern="^(back_to_main|cancel_check)$"))
    app.add_handler(CallbackQueryHandler(on_cancel_password, pattern="^cancel_password$"))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_password_input), group=0)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_answer), group=1)
    
    print("✅ Бот запущен с защитой!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()




