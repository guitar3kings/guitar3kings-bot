import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токен из переменной окружения
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

# ВАШ Telegram ID для уведомлений
ADMIN_ID = 5094488507

# URL фото для приветствия
WELCOME_PHOTO = "https://drive.usercontent.google.com/download?id=19jsxEL17vlwXsBZ8wrNzoXP8q459nOtl&export=view"

# Состояния для ConversationHandler
TIMEZONE, DAY, TIME, CUSTOM_TIMEZONE = range(4)

# Тексты сообщений
WELCOME_TEXT = """
👋 Привет!
Я бот Александра - преподавателя игры на гитаре

Я помогу вам узнать всё о занятиях и записаться на пробный урок!

Выберите интересующий вас раздел:

Возникли проблемы с ботом? Напишите нам на аккаунт: @ryder_music_academy
"""

TRIAL_LESSON_TEXT = """
🎯 **ПРОБНОЕ ЗАНЯТИЕ**

**Время:** 45-50 минут
**Формат:** онлайн по Zoom

**На пробном для новичков:**
• устройство инструмента
• постановка правой и левой рук
• первый перебор (закрепляем постановку правой)
• изучим обозначения нот и аккордов
• зажмём первые аккорды (закрепляем постановку левой)
• научимся играть перебором/боем
• всё это на примере песни, которую слушает ученик!

**На пробном для продвинутых:**
• определяем ваш текущий уровень - знакомство и постановка цели
• разберём один из вопросов/треков, который вызывает трудности
• составим индивидуальный план обучения

Всё обучение, как и пробное занятие построено на том, что мы будем изучать технические приёмы и теоретические темы на гитаре через те песни, которые вы любите.

Как показывает мой опыт, такой подход учащимся гораздо интереснее, а результативность его выше. Ведь эти песни любимы вашему сердцу, пусть они и станут вашим путеводителем в мир гитары

Полноценное обучение после пробного идёт по абонементам (актуальная цена в личных сообщениях)

**Готовы выбрать время для пробного занятия?**
"""

ABOUT_TEXT = """
**Об обучении и преподавателе**

**Александр - исполнитель, продюсер и гитарист**

Играет на гитаре > 12 лет
Опыт преподавания > 5 лет

Переучил огромное кол-во людей от 9 до 63 лет по всему миру.

У меня занимаются люди из: России, Казахстана, Армении, Тайланда, Индонезии, Германии, США и многих других стран.

Все они доверяют мне, потому что видят как отличается мой подход:

• **Теория не закон, а объяснение того, что играешь**
(Зубрить, чтобы зубрить - бред. Учи то, что реально используешь)

• **Индивидуальный подход под ваш муз. вкус и способности**

• **Настроение и ощущения на занятиях**
Слова ученика:

_"Александр, вот мы начали урок, я был немного грустный, день тяжелый. А заканчиваем его, я - довольный, будто отдохнувший. Настроение прям поднял. Спасибо!"_

Всё обучение, как и пробное занятие построено на том, что мы будем изучать технические приёмы и теоретические темы на гитаре через те песни, которые вы любите.

Как показывает мой опыт, такой подход учащимся гораздо интереснее, а результативность его выше. Ведь эти песни любимы вашему сердцу, пусть они и станут вашим путеводителем в мир гитары

**Установки в голове учеников:**

**До обучения:**
• "Играл когда-то давно, но мечта о гитаре осталась"
• "Занимался в муз. школе, но там отбили желание учиться"
• "Всегда хотел начать, но откладывал"
• "Пытался учиться сам - ничего не понятно"
• "Не знаю с чего начать, в интернете столько всего"
• "Хочу заниматься с профессионалом"

**Во время обучения:**
• "Начать никогда не поздно"
• "Учиться можно по современному, а не как в муз. школах"
• "Всё, что я слушаю, теперь могу сыграть сам"
• "Проще и легче учиться на песнях, которые любишь"
• "Теория оказывается не нудная, если знать что нужно, а что нет"
• "Обучаться надо структурировано и постоянно"

Я всем сердцем люблю музыку и всё, что с ней связано.
Люди это видят и доверяют мне.

**Записывайся, чтобы уже на пробном сыграть 1-ю песню**
"""

PREPARATION_TEXT = """
📋 **Как подготовиться к уроку?**

1️⃣ Зарегистрироваться и скачать Zoom
   👉 https://zoom.us/download

2️⃣ Скинуть 5-10 треков, которые хочется научиться играть (ссылками)

3️⃣ Внести предоплату 1000 руб. и скинуть скриншот в чат @ryder_music_academy

💳 **Реквизиты для оплаты:**

Карта Тинькофф (Т-Банк)
+7-995-347-72-83
Александр Б.

После оплаты я свяжусь с вами, чтобы утвердить время проведения пробного занятия!
"""

# Часовые пояса
TIMEZONES = {
    'utc3': 'UTC+3 (Москва)',
    'utc4': 'UTC+4 (Самара)',
    'utc5': 'UTC+5 (Екатеринбург)',
    'utc7': 'UTC+7 (Красноярск/Новосибирск)',
    'utc10': 'UTC+10 (Владивосток)',
    'custom': 'Другой часовой пояс'
}

# Дни недели на русском
WEEKDAYS_RU = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
MONTHS_RU = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']

# Временные слоты
TIME_SLOTS = [
    '12:00-13:00', '13:00-14:00', '14:00-15:00', '15:00-16:00',
    '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00',
    '20:00-21:00', '21:00-22:00', '22:00-23:00'
]

# Функция для отправки уведомлений админу
async def notify_admin(context: ContextTypes.DEFAULT_TYPE, message: str):
    """Отправляет уведомление администратору"""
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=message, parse_mode='Markdown')
        logger.info(f"Admin notification sent")
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")

# Функция для логирования действий пользователя
def log_user_action(user, action):
    """Логирует действия пользователя"""
    username = user.username if user.username else "без username"
    full_name = f"{user.first_name} {user.last_name if user.last_name else ''}".strip()
    log_message = f"User @{username} ({full_name}, ID: {user.id}) - {action}"
    logger.info(log_message)
    return log_message

# Функция для получения дат на 2 недели вперёд
def get_available_dates(offset=0):
    """Возвращает список дат начиная с сегодня + offset до 14 дней"""
    dates = []
    start_date = datetime.now().date() + timedelta(days=offset)
    for i in range(7):
        date = start_date + timedelta(days=i)
        if (date - datetime.now().date()).days <= 14:
            dates.append(date)
    return dates

def format_date(date):
    """Форматирует дату в формат 'Понедельник 18 ноября'"""
    weekday = WEEKDAYS_RU[date.weekday()]
    day = date.day
    month = MONTHS_RU[date.month - 1]
    return f"{weekday} {day} {month}"

# Клавиатуры
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎯 Записаться на пробный урок", callback_data='trial')],
        [InlineKeyboardButton("👨‍🏫 Об обучении и преподавателе", callback_data='about')],
        [InlineKeyboardButton("📋 Как подготовиться к пробному?", callback_data='preparation')],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_trial_keyboard():
    keyboard = [
        [InlineKeyboardButton("📅 Записаться прямо сейчас", callback_data='schedule')],
        [InlineKeyboardButton("⬅️ Вернуться в меню", callback_data='back_to_main')],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_about_keyboard():
    keyboard = [
        [InlineKeyboardButton("📅 Записаться на пробное сейчас", callback_data='schedule')],
        [InlineKeyboardButton("⬅️ Вернуться в меню", callback_data='back_to_main')],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_preparation_keyboard():
    keyboard = [
        [InlineKeyboardButton("📅 Записаться на пробное сейчас", callback_data='schedule')],
        [InlineKeyboardButton("⬅️ Вернуться в меню", callback_data='back_to_main')],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_timezone_keyboard():
    keyboard = []
    for key, value in TIMEZONES.items():
        keyboard.append([InlineKeyboardButton(value, callback_data=f'tz_{key}')])
    keyboard.append([InlineKeyboardButton("⬅️ Отмена", callback_data='back_to_main')])
    return InlineKeyboardMarkup(keyboard)

def get_days_keyboard(offset=0):
    keyboard = []
    dates = get_available_dates(offset)
    
    for date in dates:
        date_str = format_date(date)
        keyboard.append([InlineKeyboardButton(date_str, callback_data=f'date_{date.isoformat()}')])
    
    nav_buttons = []
    if offset > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Раньше", callback_data=f'dates_prev_{offset}'))
    if offset + 7 <= 14:
        nav_buttons.append(InlineKeyboardButton("Позже ➡️", callback_data=f'dates_next_{offset}'))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='schedule')])
    return InlineKeyboardMarkup(keyboard)

def get_time_keyboard():
    keyboard = []
    for i in range(0, len(TIME_SLOTS), 2):
        row = []
        row.append(InlineKeyboardButton(TIME_SLOTS[i], callback_data=f'time_{i}'))
        if i + 1 < len(TIME_SLOTS):
            row.append(InlineKeyboardButton(TIME_SLOTS[i + 1], callback_data=f'time_{i + 1}'))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='back_to_days')])
    return InlineKeyboardMarkup(keyboard)

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение с фото"""
    user = update.effective_user
    log_user_action(user, "Запустил бота /start")
    
    await notify_admin(
        context,
        f"🆕 *Новый пользователь!*\n"
        f"👤 Имя: {user.first_name} {user.last_name if user.last_name else ''}\n"
        f"🔗 Username: @{user.username if user.username else 'нет'}\n"
        f"🆔 ID: `{user.id}`"
    )
    
    try:
        await update.message.reply_photo(
            photo=WELCOME_PHOTO,
            caption=WELCOME_TEXT,
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Failed to send photo: {e}")
        await update.message.reply_text(
            WELCOME_TEXT,
            reply_markup=get_main_keyboard()
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    if query.data == 'trial':
        log_user_action(user, "Просмотрел 'Пробное занятие'")
        await notify_admin(context, f"🎯 Пользователь @{user.username or user.id} просмотрел 'Пробное занятие'")
        await query.message.reply_text(TRIAL_LESSON_TEXT, parse_mode='Markdown', reply_markup=get_trial_keyboard())
    
    elif query.data == 'about':
        log_user_action(user, "Просмотрел 'Об обучении'")
        await notify_admin(context, f"👨‍🏫 Пользователь @{user.username or user.id} просмотрел 'Об обучении'")
        await query.message.reply_text(ABOUT_TEXT, parse_mode='Markdown', reply_markup=get_about_keyboard())
    
    elif query.data == 'preparation':
        log_user_action(user, "Просмотрел 'Подготовка'")
        await notify_admin(context, f"📋 Пользователь @{user.username or user.id} просмотрел 'Подготовка'")
        await query.message.reply_text(PREPARATION_TEXT, parse_mode='Markdown', reply_markup=get_preparation_keyboard())
    
    elif query.data == 'schedule':
        log_user_action(user, "Начал запись на занятие")
        await notify_admin(context, f"📅 Пользователь @{user.username or user.id} начал запись на занятие")
        await query.message.reply_text(
            "🌍 **Выберите ваш часовой пояс:**",
            parse_mode='Markdown',
            reply_markup=get_timezone_keyboard()
        )
        return TIMEZONE
    
    elif query.data == 'back_to_main':
        try:
            await query.message.reply_photo(
                photo=WELCOME_PHOTO,
                caption=WELCOME_TEXT,
                reply_markup=get_main_keyboard()
            )
        except:
            await query.message.reply_text(WELCOME_TEXT, reply_markup=get_main_keyboard())
        return ConversationHandler.END

# Обработчики процесса записи
async def timezone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора часового пояса"""
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    if query.data == 'tz_custom':
        await query.message.reply_text(
            "🕐 **Укажите ваш часовой пояс**\n\n"
            "Напишите в формате:\n"
            "`+3` (плюс 3 часа от Москвы)\n"
            "`-2` (минус 2 часа от Москвы)\n"
            "`0` (по Москве)",
            parse_mode='Markdown'
        )
        return CUSTOM_TIMEZONE
    
    tz_key = query.data.replace('tz_', '')
    context.user_data['timezone'] = TIMEZONES[tz_key]
    context.user_data['date_offset'] = 0
    log_user_action(user, f"Выбрал часовой пояс: {TIMEZONES[tz_key]}")
    
    await query.message.reply_text(
        f"✅ Часовой пояс: **{TIMEZONES[tz_key]}**\n\n"
        "📅 **Выберите день:**",
        parse_mode='Markdown',
        reply_markup=get_days_keyboard(0)
    )
    return DAY

async def custom_timezone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода произвольного часового пояса"""
    user = update.effective_user
    text = update.message.text.strip()
    
    try:
        offset = int(text)
        timezone_str = f"UTC{'+' if offset >= 0 else ''}{offset + 3} (Москва{'+' if offset >= 0 else ''}{offset})"
        context.user_data['timezone'] = timezone_str
        context.user_data['date_offset'] = 0
        log_user_action(user, f"Указал часовой пояс: {timezone_str}")
        
        await update.message.reply_text(
            f"✅ Часовой пояс: **{timezone_str}**\n\n"
            "📅 **Выберите день:**",
            parse_mode='Markdown',
            reply_markup=get_days_keyboard(0)
        )
        return DAY
    except:
        await update.message.reply_text(
            "❌ Неверный формат!\n\n"
            "Напишите число от -12 до +12\n"
            "Например: `+3` или `-5`",
            parse_mode='Markdown'
        )
        return CUSTOM_TIMEZONE

async def day_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора дня"""
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    if query.data.startswith('dates_prev_'):
        offset = int(query.data.split('_')[2])
        new_offset = max(0, offset - 7)
        context.user_data['date_offset'] = new_offset
        await query.edit_message_text(
            f"✅ Часовой пояс: **{context.user_data['timezone']}**\n\n"
            "📅 **Выберите день:**",
            parse_mode='Markdown',
            reply_markup=get_days_keyboard(new_offset)
        )
        return DAY
    
    elif query.data.startswith('dates_next_'):
        offset = int(query.data.split('_')[2])
        new_offset = min(14, offset + 7)
        context.user_data['date_offset'] = new_offset
        await query.edit_message_text(
            f"✅ Часовой пояс: **{context.user_data['timezone']}**\n\n"
            "📅 **Выберите день:**",
            parse_mode='Markdown',
            reply_markup=get_days_keyboard(new_offset)
        )
        return DAY
    
    elif query.data == 'back_to_timezone':
        await query.message.reply_text(
            "🌍 **Выберите ваш часовой пояс:**",
            parse_mode='Markdown',
            reply_markup=get_timezone_keyboard()
        )
        return TIMEZONE
    
    date_str = query.data.replace('date_', '')
    selected_date = datetime.fromisoformat(date_str).date()
    context.user_data['date'] = selected_date
    context.user_data['date_formatted'] = format_date(selected_date)
    log_user_action(user, f"Выбрал день: {format_date(selected_date)}")
    
    await query.message.reply_text(
        f"✅ Часовой пояс: **{context.user_data['timezone']}**\n"
        f"✅ День: **{format_date(selected_date)}**\n\n"
        "🕐 **Выберите удобное время:**",
        parse_mode='Markdown',
        reply_markup=get_time_keyboard()
    )
    return TIME

async def time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора времени и завершение записи"""
    query = update.callback_query
    user = query.from_user
    await query.answer()
    
    if query.data == 'back_to_days':
        offset = context.user_data.get('date_offset', 0)
        await query.message.reply_text(
            f"✅ Часовой пояс: **{context.user_data['timezone']}**\n\n"
            "📅 **Выберите день:**",
            parse_mode='Markdown',
            reply_markup=get_days_keyboard(offset)
        )
        return DAY
    
    time_index = int(query.data.replace('time_', ''))
    selected_time = TIME_SLOTS[time_index]
    
    log_user_action(user, f"Записался: {context.user_data['date_formatted']}, {selected_time}, {context.user_data['timezone']}")
    
    await query.message.reply_text(
        f"✅ **Заявка принята!**\n\n"
        f"📅 День: **{context.user_data['date_formatted']}**\n"
        f"🕐 Время: **{selected_time}**\n"
        f"🌍 Часовой пояс: **{context.user_data['timezone']}**\n\n"
        f"Александр свяжется с вами в ближайшее время для подтверждения записи! 🎸\n\n"
        f"Если нужно что-то изменить или задать вопрос - просто напишите сюда в чат.",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )
    
    username = f"@{user.username}" if user.username else "без username"
    full_name = f"{user.first_name} {user.last_name if user.last_name else ''}".strip()
    
    await notify_admin(
        context,
        f"🎉 *НОВАЯ ЗАЯВКА НА ЗАНЯТИЕ!*\n\n"
        f"👤 *Клиент:*\n"
        f"Имя: {full_name}\n"
        f"Username: {username}\n"
        f"ID: `{user.id}`\n\n"
        f"📅 *Детали записи:*\n"
        f"День: {context.user_data['date_formatted']}\n"
        f"Время: {selected_time}\n"
        f"Часовой пояс: {context.user_data['timezone']}\n\n"
        f"Свяжитесь с клиентом: {username if user.username else f'tg://user?id={user.id}'}"
    )
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена процесса записи"""
    query = update.callback_query
    if query:
        await query.answer()
        try:
            await query.message.reply_photo(
                photo=WELCOME_PHOTO,
                caption=WELCOME_TEXT,
                reply_markup=get_main_keyboard()
            )
        except:
            await query.message.reply_text(WELCOME_TEXT, reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text(WELCOME_TEXT, reply_markup=get_main_keyboard())
    return ConversationHandler.END

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user = update.effective_user
    user_message = update.message.text
    
    log_user_action(user, f"Написал сообщение: {user_message}")
    
    username = f"@{user.username}" if user.username else "без username"
    full_name = f"{user.first_name} {user.last_name if user.last_name else ''}".strip()
    
    await notify_admin(
        context,
        f"💬 *Новое сообщение от клиента!*\n\n"
        f"👤 От: {full_name} ({username})\n"
        f"ID: `{user.id}`\n\n"
        f"📝 Сообщение:\n{user_message}\n\n"
        f"Ответьте клиенту: {username if user.username else f'tg://user?id={user.id}'}"
    )
    
    await update.message.reply_text(
        "Спасибо за сообщение! ✅\n\n"
        "Александр получил ваше сообщение и ответит в ближайшее время.\n\n"
        "А пока можете посмотреть информацию в меню:",
        reply_markup=get_main_keyboard()
    )

def main():
    """Запуск бота"""
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found!")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    # ConversationHandler для процесса записи
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern='^schedule$')],
        states={
            TIMEZONE: [CallbackQueryHandler(timezone_handler, pattern='^tz_')],
            CUSTOM_TIMEZONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_timezone_handler)],
            DAY: [CallbackQueryHandler(day_handler)],
            TIME: [CallbackQueryHandler(time_handler, pattern='^time_|back_to_days$')],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^back_to_main$')],
    )
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Бот запущен и работает 24/7!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
