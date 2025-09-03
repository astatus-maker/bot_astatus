import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes, CallbackQueryHandler
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import config
import database as db

# Включим логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
TYPING_PROBLEM, UPLOADING_PHOTO = range(2)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = user.username
    full_name = user.full_name

    # Добавляем пользователя в БД
    db.add_user(user_id, username, full_name)

    # Проверяем, является ли пользователь админом (чтобы сразу дать меню менеджера)
    if user_id in config.ADMIN_IDS:
        db.update_user_role(user_id, 'manager')
        keyboard = [['📋 Создать заявку'], ['👨‍💼 Специалист']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_html(
            rf"Привет {user.mention_html()}! Вы авторизованы как специалист.",
            reply_markup=reply_markup
        )
    else:
        # Обычная клавиатура для клиента
        keyboard = [['📋 Создать заявку'], ['📊 Мои заявки']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_html(
            rf"Привет {user.mention_html()}! Я бот для заявок.",
            reply_markup=reply_markup
        )

# Обработчик текстовых сообщений (кнопки главного меню)
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)

    if text == '📋 Создать заявку':
        await update.message.reply_text(
            "Опишите проблему:",
            reply_markup=ReplyKeyboardRemove()
        )
        return TYPING_PROBLEM

    elif text == '📊 Мои заявки':
        requests = db.get_requests(user_id=user_id)
        if not requests:
            await update.message.reply_text("У вас нет активных заявок.")
            return ConversationHandler.END
        for req in requests:
            status_map = {'new': '🆕 Новая', 'assigned': '👨‍🔧 Назначена', 'in_progress': '🔧 В работе', 'done': '✅ Выполнена', 'confirmed': '✔️ Подтверждена'}
            status_text = status_map.get(req[3], req[3])
            message_text = f"Заявка #{req[0]}\nПроблема: {req[2]}\nСтатус: {status_text}"
            await update.message.reply_text(message_text)
        return ConversationHandler.END

    elif text == '👨‍💼 Специалист' and user_data[3] == 'manager':
        keyboard = [
            ['🆕 Новые заявки', '🔧 В работе'],
            ['✅ На проверке', '📊 Все заявки']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Панель менеджера:", reply_markup=reply_markup)
        return ConversationHandler.END

    elif text == '🆕 Новые заявки' and user_data[3] == 'manager':
        requests = db.get_requests(status='new')
        if not requests:
            await update.message.reply_text("Новых заявок нет.")
            return ConversationHandler.END
        for req in requests:
            message_text = f"🆕 Новая заявка #{req[0]}\nОт: @{req[1]}\nПроблема: {req[2]}"
            keyboard = [[InlineKeyboardButton("Назначить мастера", callback_data=f"assign_{req[0]}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if req[5]: # Если есть фото
                await update.message.reply_photo(req[5], caption=message_text, reply_markup=reply_markup)
            else:
                await update.message.reply_text(message_text, reply_markup=reply_markup)
        return ConversationHandler.END

# Обработка описания проблемы
async def receive_problem_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    problem_text = update.message.text
    context.user_data['problem_text'] = problem_text
    await update.message.reply_text("Теперь пришлите фото проблемы (или нажмите /skip если фото не нужно).")
    return UPLOADING_PHOTO

# Пропуск фото
async def skip_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    problem_text = context.user_data['problem_text']
    req_id = db.add_request(user_id, problem_text)
    await update.message.reply_text(f"Заявка #{req_id} создана!")
    return ConversationHandler.END

# Получение фото
async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    problem_text = context.user_data['problem_text']
    photo_file = await update.message.photo[-1].get_file()
    photo_path = f"photos/before_{user_id}_{update.message.message_id}.jpg"
    await photo_file.download_to_drive(photo_path)
    req_id = db.add_request(user_id, problem_text, photo_path)
    await update.message.reply_text(f"Заявка #{req_id} создана с фото!")
    return ConversationHandler.END

# Обработка нажатий на inline-кнопки (назначение мастера)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data.startswith('assign_'):
        req_id = int(data.split('_')[1])
        # Здесь должен быть код для выбора мастера из БД и назначения заявки
        # Для примера просто назначим на статичного мастера (id=999)
        db.assign_request(req_id, 999)
        await query.edit_message_caption(caption=query.message.caption + "\n\n✅ ")
    # ... можно добавить другие обработчики кнопок

# Команда /cancel для отмены любого состояния
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Действие отменено.', reply_markup=ReplyKeyboardMarkup([['📋 Создать заявку', '📊 Мои заявки']], resize_keyboard=True))
    return ConversationHandler.END

def main():
    # Создаем Application
    application = Application.builder().token(config.BOT_TOKEN).build()

    # ConversationHandler для создания заявки
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^(📋 Создать заявку)$'), handle_main_menu)],
        states={
            TYPING_PROBLEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_problem_description)],
            UPLOADING_PHOTO: [
                MessageHandler(filters.PHOTO, receive_photo),
                CommandHandler('skip', skip_photo)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Запускаем бота в режиме поллинга (для локального тестирования)
    print("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()
