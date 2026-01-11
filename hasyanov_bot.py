import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import os

# 🔑 Вставь свой токен от @BotFather (через переменную окружения)
TOKEN = os.getenv("TOKEN")

# 📁 Пути к папкам
HW_DIR = "./дз/"
NOTES_DIR = "./конспекты/"

# 🔹 Список номеров (25 штук)
NUMBERS = list(range(1, 7)) + ["7_изобр", "7_звуки"] + list(range(8, 19)) + ["19_21"] + list(range(22, 28))

# 🔹 Номера ДЗ, у которых есть папка с дополнительными файлами
HW_WITH_FOLDER = {3, 9, 10, 17, 18, 22}

# 📝 Ответы
homework = {
    # ДЗ 1
    1: ["14", "25", "17", "18", "124", "25", "42", "18", "68", "46"],
    # ... (все остальные ответы — как у тебя)
    "19_21": ["27 24 26 23", "118 113 117 112", "45 40 44 39 43", "8 720 19", 
              "28 48 54 47", "17 11 23 6", "13 10 19 6", "28 25 52 33", 
              "40 10 39 7", "54 98 106 97"],
}

# 📊 Состояние
user_checking = {}

# 📜 Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 📥 Отправка PDF
async def send_pdf(query, file_path: str, caption: str = ""):
    try:
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                await query.message.reply_document(document=f, caption=caption)
                return True
        else:
            await query.message.reply_text(f"❌ Файл не найден: `{file_path}`", parse_mode="Markdown")
            return False
    except Exception as e:
        logger.error(f"Ошибка при отправке PDF: {e}")
        await query.message.reply_text(f"❌ Ошибка при отправке файла: {e}")
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
                                    caption=f"📎 {filename}"
                                )
                        except Exception as e:
                            await query.message.reply_text(f"⚠️ Не удалось отправить {filename}: {e}")
            else:
                await query.message.reply_text(f"ℹ️ Папка 'файлы_{hw_num}' не найдена — файлы отсутствуют.")

# 📖 Конспект
async def send_note_pdf(query, note_num: int | str):
    if str(note_num) in ["19", "20", "21", "19_21", "1921"]:
        filename = "19_21"
    else:
        filename = str(note_num)
    note_path = os.path.join(NOTES_DIR, f"Конспект_{filename}.pdf")
    await send_pdf(query, note_path, f"📝 Конспект №{filename}")

# 🏁 Главное меню
async def show_main_menu(chat_id, context: ContextTypes.DEFAULT_TYPE, message_text: str = "👋 Чем займёмся сегодня?"):
    keyboard = [
        [InlineKeyboardButton("📚 Получить ДЗ", callback_data="action_get")],
        [InlineKeyboardButton("🔍 Проверить ДЗ", callback_data="action_check")],
        [InlineKeyboardButton("📝 Конспекты", callback_data="action_notes")],
    ]
    await context.bot.send_message(
        chat_id=chat_id,
        text=message_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# 🏁 /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update.effective_chat.id, context)

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
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

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
        await query.edit_message_text(
            f"✅ Проверим ДЗ №{hw_num_str}\n📌 Задание #1:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ✍️ Ввод ответа
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
        await update.message.reply_text(f"❌ ДЗ №{hw_key} не найдено в базе")
        return
    correct_answers = homework[hw_key]
    if task_num > len(correct_answers):
        await update.message.reply_text(f"❌ Задание №{task_num} не найдено")
        return
    correct_ans = str(correct_answers[task_num - 1]).strip()
    def normalize(s: str) -> str:
        parts = s.lower().split()
        return " ".join(parts)
    user_norm = normalize(user_input)
    correct_norm = normalize(correct_ans)
    is_correct = user_norm == correct_norm
    if is_correct:
        await update.message.reply_text("✅ Верно!")
    else:
        await update.message.reply_text(f"❌ Неверно.")
    if "results" not in user_checking[user_id]:
        user_checking[user_id]["results"] = []
    user_checking[user_id]["results"].append(is_correct)
    next_task = task_num + 1
    if next_task <= len(correct_answers):
        user_checking[user_id]["task"] = next_task
        await update.message.reply_text(f"📌 Задание #{next_task}:")
    else:
        results = user_checking[user_id]["results"]
        correct_count = sum(results)
        total = len(results)
        if correct_count == total:
            phrase = "Ты молодец!"
        else:
            phrase = "Тренеруйся. Есть ошибки."
        summary = f"✅ ДЗ_{hw_key} решено: {correct_count}/{total}\n«{phrase}»"
        await update.message.reply_text(summary)
        await update.message.reply_text(
            "📤 Скопируй это сообщение и пришли мне в личку!\n"
            "Я проверю твой прогресс 😊"
        )
        del user_checking[user_id]
        await show_main_menu(update.effective_chat.id, context, "🎉 Проверка завершена! Что дальше?")

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

# 🚀 Запуск
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(on_action, pattern="^action_(get|check|notes)$"))
    app.add_handler(CallbackQueryHandler(on_get_selected, pattern="^action_get_"))
    app.add_handler(CallbackQueryHandler(on_check_selected, pattern="^action_check_"))
    app.add_handler(CallbackQueryHandler(on_note_selected, pattern="^action_notes_"))
    app.add_handler(CallbackQueryHandler(on_back_button, pattern="^(back_to_main|cancel_check)$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_answer))
    print("✅ Бот запущен!")
    await app.start()
    await app.updater.start_polling()
    await app.updater.stop()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
