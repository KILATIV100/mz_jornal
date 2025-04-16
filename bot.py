import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from telegram.ext import CallbackContext

# Токен бота
TOKEN = 'YOUR_BOT_TOKEN'

# Встановлюємо логування
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Стани для ConversationHandler
SELECT_LANGUAGE, SELECT_JOURNAL, INPUT_OBJECT_NAME, INPUT_DESCRIPTION, INPUT_SENDER_RECEIVER, FILE_ATTACHMENT = range(6)

# Підключення до бази даних SQLite
def create_db():
    conn = sqlite3.connect('letters.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS letters (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        type TEXT,
                        date TEXT,
                        number TEXT,
                        object_name TEXT,
                        description TEXT,
                        sender_receiver TEXT,
                        status TEXT,
                        file_path TEXT)''')
    conn.commit()
    conn.close()

# Генерація номера листа
def generate_letter_number():
    current_year = datetime.now().year
    conn = sqlite3.connect('letters.db')
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM letters WHERE strftime('%Y', date) = '{current_year}'")
    count = cursor.fetchone()[0] + 1
    letter_number = f"{count}/{current_year}"
    conn.close()
    return letter_number

# Стартова команда
async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("Українська", callback_data='ukrainian')],
        [InlineKeyboardButton("English", callback_data='english')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Please select your language / Будь ласка, виберіть мову", reply_markup=reply_markup)
    return SELECT_LANGUAGE

# Обробка вибору мови
async def select_language(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'ukrainian':
        context.user_data['language'] = 'uk'
    else:
        context.user_data['language'] = 'en'

    keyboard = [
        [InlineKeyboardButton("Вхідні листи", callback_data='inbound')],
        [InlineKeyboardButton("Вихідні листи", callback_data='outbound')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Select journal / Виберіть журнал", reply_markup=reply_markup)
    return SELECT_JOURNAL

# Вибір журналу
async def select_journal(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'inbound':
        context.user_data['journal'] = 'inbound'
    else:
        context.user_data['journal'] = 'outbound'
    
    await query.edit_message_text("Please enter the object name / Введіть назву об'єкта:")
    return INPUT_OBJECT_NAME

# Запит на введення назви об'єкта
async def input_object_name(update: Update, context: CallbackContext):
    await update.message.reply_text("Please enter the object name / Введіть назву об'єкта:")
    return INPUT_OBJECT_NAME

# Запит на введення опису
async def input_description(update: Update, context: CallbackContext):
    context.user_data['object_name'] = update.message.text
    await update.message.reply_text("Please enter a description of the letter / Введіть короткий опис листа:")
    return INPUT_DESCRIPTION

# Запит на введення від кого/кому
async def input_sender_receiver(update: Update, context: CallbackContext):
    context.user_data['description'] = update.message.text
    await update.message.reply_text("Please enter the sender/receiver name / Введіть відправника/одержувача:")
    return INPUT_SENDER_RECEIVER

# Запит на прикріплення файлу
async def file_attachment(update: Update, context: CallbackContext):
    context.user_data['sender_receiver'] = update.message.text
    await update.message.reply_text("Please attach a file if needed / Будь ласка, прикріпіть файл (якщо потрібно).")
    return FILE_ATTACHMENT

# Збереження даних у базу даних
async def save_data(update: Update, context: CallbackContext):
    letter_data = context.user_data
    letter_number = generate_letter_number()
    letter_data['letter_number'] = letter_number
    conn = sqlite3.connect('letters.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO letters (type, date, number, object_name, description, sender_receiver, status, file_path)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                   (letter_data['journal'], datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    letter_data['letter_number'], letter_data['object_name'], letter_data['description'],
                    letter_data['sender_receiver'], 'pending', None))  # Replace 'None' with file path if available
    conn.commit()
    conn.close()
    await update.message.reply_text(f"Your letter has been registered. Letter number: {letter_number} / Ваш лист було зареєстровано.")
    return ConversationHandler.END

# Функція для скасування
async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("Operation canceled / Операцію скасовано.")
    return ConversationHandler.END

# Основна функція
def main():
    create_db()
    
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_LANGUAGE: [CallbackQueryHandler(select_language)],
            SELECT_JOURNAL: [CallbackQueryHandler(select_journal)],
            INPUT_OBJECT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_object_name)],
            INPUT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_description)],
            INPUT_SENDER_RECEIVER: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_sender_receiver)],
            FILE_ATTACHMENT: [MessageHandler(filters.Document.ALL, file_attachment)],  # Listen for file attachment
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()
