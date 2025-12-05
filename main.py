import logging
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from datetime import datetime, timedelta

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройки
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ADMIN_ID = 5094488507
WELCOME_PHOTO = "https://drive.usercontent.google.com/download?id=19jsxEL17vlwXsBZ8wrNzoXP8q459nOtl&export=view"
SCHEDULE_FILE = 'schedule.json'

# Состояния
LEVEL, INSTRUMENT, TIMEZONE, DAY, TIME, CUSTOM_TIMEZONE = range(6)
ADMIN_MENU, ADMIN_BLOCK_TYPE, ADMIN_BLOCK_DAY, ADMIN_BLOCK_TIME = range(6, 10)
ADMIN_UNBLOCK_TYPE, ADMIN_UNBLOCK_DAY, ADMIN_UNBLOCK_TIME = range(10, 13)

# Расписание по умолчанию
DEFAULT_WEEKLY_SCHEDULE = {
    'Monday': [],
    'Tuesday': ['13:00-14:00', '16:00-17:00', '20:00-21:00'],
    'Wednesday': ['14:00-15:00', '18:00-19:00', '19:00-20:00', '20:00-21:00', '21:00-22:00'],
    'Thursday': ['19:00-20:00', '20:00-21:00'],
    'Friday': ['13:00-14:00', '14:00-15:00', '16:00-17:00', '19:00-20:00', '20:00-21:00'],
    'Saturday': ['15:00-16:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00'],
    'Sunday': ['19:00-20:00', '20:00-21:00']
}

# Функции работы с расписанием
def load_schedule():
    try:
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'weekly_blocked': DEFAULT_WEEKLY_SCHEDULE.copy(), 'specific_dates': {}}

def save_schedule(schedule):
    with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

SCHEDULE = load_schedule()

# Константы
TIMEZONES = {
    'utc3': 'UTC+3 (Москва)',
    'utc4': 'UTC+4 (Самара)',
    'utc5': 'UTC+5 (Екатеринбург)',
    'utc7': 'UTC+7 (Красноярск/Новосибирск)',
    'utc10': 'UTC+10 (Владивосток)',
    'custom': 'Другой часовой пояс'
}

WEEKDAYS_RU = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
WEEKDAYS_EN = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MONTHS_RU = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
TIME_SLOTS = ['12:00-13:00', '13:00-14:00', '14:00-15:00', '15:00-16:00', '16:00-17:00', '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00', '21:00-22:00', '22:00-23:00']

# Тексты сообщений
WELCOME_TEXT = """👋 Привет!
Я бот Александра - преподавателя игры на гитаре

Я помогу вам узнать всё о занятиях и записаться на пробный урок!

Выберите интересующий вас раздел:

Возникли проблемы с ботом? Напишите нам: @ryder_music_academy"""

TRIAL_TEXT = """🎯 **ПРОБНОЕ ЗАНЯТИЕ**

**Время:** 45-50 минут
**Формат:** онлайн по Zoom

**На пробном для новичков:**
• устройство инструмента
• постановка правой и левой рук
• первый перебор
• изучим обозначения нот и аккордов
• зажмём первые аккорды
• научимся играть перебором/боем
• всё это на примере песни, которую слушает ученик!

**На пробном для продвинутых:**
• определяем ваш текущий уровень
• разберём один из вопросов/треков
• составим индивидуальный план обучения

**Готовы выбрать время для пробного занятия?**"""

ABOUT_TEXT = """**Об обучении и преподавателе**

**Александр - исполнитель, продюсер и гитарист**

Играет на гитаре > 12 лет
Опыт преподавания > 5 лет

Переучил людей от 9 до 63 лет по всему миру.

**Записывайся, чтобы уже на пробном сыграть 1-ю песню**"""

PREPARATION_TEXT = """📋 **Как подготовиться к уроку?**

1️⃣ Зарегистрироваться и скачать Zoom
   👉 https://zoom.us/download

2️⃣ Скинуть 5-10 треков (ссылками)

3️⃣ Внести предоплату 1000 руб. и скинуть скриншот в чат @ryder_music_academy

💳 **Реквизиты:**
Карта Тинькофф (Т-Банк)
+7-995-347-72-83
Александр Б."""

NO_INSTRUMENT_TEXT = """🎸 **Отлично!**

Скоро с вами свяжется Александр в личных сообщениях, чтобы порекомендовать какой инструмент лучше приобрести!

Александр напишет вам в течение 24 часов!"""

# Вспомогательные функции
def is_slot_blocked(date, time_slot):
    date_str = date.isoformat()
    if date_str in SCHEDULE['specific_dates'] and time_slot in SCHEDULE['specific_dates'][date_str]:
        return True
    weekday = WEEKDAYS_EN[date.weekday()]
    return time_slot in SCHEDULE['weekly_blocked'].get(weekday, [])

def get_available_slots(date):
    return [slot for slot in TIME_SLOTS if not is_slot_blocked(date, slot)]

async def notify_admin(context, message):
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=message, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Notify error: {e}")

def log_user_action(user, action):
    logger.info(f"User @{user.username or 'none'} ({user.id}) - {action}")

def get_available_dates(offset=0):
    dates = []
    start_date = datetime.now().date() + timedelta(days=offset)
    for i in range(7):
        date = start_date + timedelta(days=i)
        if (date - datetime.now().date()).days <= 14 and get_available_slots(date):
            dates.append(date)
    return dates

def format_date(date):
    return f"{WEEKDAYS_RU[date.weekday()]} {date.day} {MONTHS_RU[date.month - 1]}"

# Клавиатуры
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 Записаться на пробный урок", callback_data='trial')],
        [InlineKeyboardButton("👨‍🏫 Об обучении и преподавателе", callback_data='about')],
        [InlineKeyboardButton("📋 Как подготовиться?", callback_data='preparation')]
    ])

def get_trial_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Записаться прямо сейчас", callback_data='start_booking')],
        [InlineKeyboardButton("⬅️ Вернуться в меню", callback_data='back_to_main')]
    ])

def get_level_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🆕 Я новичок", callback_data='level_beginner')],
        [InlineKeyboardButton("🎸 Уже играю / есть опыт", callback_data='level_experienced')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='trial')]
    ])

def get_instrument_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎸 Электрогитара", callback_data='inst_electric')],
        [InlineKeyboardButton("🎼 Обычная гитара", callback_data='inst_acoustic')],
        [InlineKeyboardButton("❌ Пока нет инструмента", callback_data='inst_none')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='back_to_level')]
    ])

def get_timezone_keyboard():
    keyboard = [[InlineKeyboardButton(v, callback_data=f'tz_{k}')] for k, v in TIMEZONES.items()]
    keyboard.append([InlineKeyboardButton("⬅️ Отмена", callback_data='back_to_main')])
    return InlineKeyboardMarkup(keyboard)

def get_days_keyboard(offset=0):
    dates = get_available_dates(offset)
    keyboard = []
    for date in dates:
        count = len(get_available_slots(date))
        keyboard.append([InlineKeyboardButton(f"{format_date(date)} ({count} слотов)", callback_data=f'date_{date.isoformat()}')])
    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton("⬅️ Раньше", callback_data=f'dates_prev_{offset}'))
    if offset + 7 <= 14:
        nav.append(InlineKeyboardButton("Позже ➡️", callback_data=f'dates_next_{offset}'))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='back_to_timezone')])
    return InlineKeyboardMarkup(keyboard)

def get_time_keyboard(date):
    slots = get_available_slots(date)
    keyboard = []
    for i in range(0, len(slots), 2):
        row = [InlineKeyboardButton(slots[i], callback_data=f'time_{slots[i]}')] 
        if i + 1 < len(slots):
            row.append(InlineKeyboardButton(slots[i + 1], callback_data=f'time_{slots[i + 1]}'))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='back_to_days')])
    return InlineKeyboardMarkup(keyboard)

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    log_user_action(user, "Start")
    await notify_admin(context, f"🆕 *Новый пользователь!*\n👤 {user.first_name}\n🔗 @{user.username or 'нет'}\n🆔 `{user.id}`")
    try:
        await update.message.reply_photo(photo=WELCOME_PHOTO, caption=WELCOME_TEXT, reply_markup=get_main_keyboard())
    except:
        await update.message.reply_text(WELCOME_TEXT, reply_markup=get_main_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'trial':
        await query.message.reply_text(TRIAL_TEXT, parse_mode='Markdown', reply_markup=get_trial_keyboard())
    elif query.data == 'about':
        await query.message.reply_text(ABOUT_TEXT, parse_mode='Markdown', reply_markup=get_trial_keyboard())
    elif query.data == 'preparation':
        await query.message.reply_text(PREPARATION_TEXT, parse_mode='Markdown', reply_markup=get_trial_keyboard())
    elif query.data == 'start_booking':
        log_user_action(query.from_user, "Booking")
        await query.message.reply_text("**Вы новичок или уже имеете опыт?**", parse_mode='Markdown', reply_markup=get_level_keyboard())
        return LEVEL
    elif query.data == 'back_to_main':
        try:
            await query.message.reply_photo(photo=WELCOME_PHOTO, caption=WELCOME_TEXT, reply_markup=get_main_keyboard())
        except:
            await query.message.reply_text(WELCOME_TEXT, reply_markup=get_main_keyboard())
        return ConversationHandler.END

async def level_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    level = "Новичок" if query.data == 'level_beginner' else "С опытом"
    context.user_data['level'] = level
    log_user_action(query.from_user, f"Level: {level}")
    await query.message.reply_text("**Какой у вас инструмент?**", parse_mode='Markdown', reply_markup=get_instrument_keyboard())
    return INSTRUMENT

async def instrument_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    if query.data == 'inst_none':
        log_user_action(user, "No instrument")
        await query.message.reply_text(NO_INSTRUMENT_TEXT, parse_mode='Markdown', reply_markup=get_main_keyboard())
        await notify_admin(context, f"⚠️ *Клиент без инструмента!*\n👤 {user.first_name}\n🔗 @{user.username or 'нет'}")
        return ConversationHandler.END
    
    inst = "Электрогитара" if query.data == 'inst_electric' else "Акустика/Классика"
    context.user_data['instrument'] = inst
    log_user_action(user, f"Instrument: {inst}")
    await query.message.reply_text("🌍 **Выберите ваш часовой пояс:**", parse_mode='Markdown', reply_markup=get_timezone_keyboard())
    return TIMEZONE

async def timezone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'tz_custom':
        await query.message.reply_text("🕐 Напишите в формате: `+3` или `-2`", parse_mode='Markdown')
        return CUSTOM_TIMEZONE
    
    tz_key = query.data.replace('tz_', '')
    context.user_data['timezone'] = TIMEZONES[tz_key]
    context.user_data['date_offset'] = 0
    await query.message.reply_text(f"✅ Часовой пояс: **{TIMEZONES[tz_key]}**\n\n📅 **Выберите день:**", parse_mode='Markdown', reply_markup=get_days_keyboard(0))
    return DAY

async def custom_timezone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        offset = int(update.message.text.strip())
        tz = f"UTC{'+' if offset >= 0 else ''}{offset + 3} (Москва{'+' if offset >= 0 else ''}{offset})"
        context.user_data['timezone'] = tz
        context.user_data['date_offset'] = 0
        await update.message.reply_text(f"✅ Часовой пояс: **{tz}**\n\n📅 **Выберите день:**", parse_mode='Markdown', reply_markup=get_days_keyboard(0))
        return DAY
    except:
        await update.message.reply_text("❌ Неверный формат! Напишите число: `+3` или `-5`", parse_mode='Markdown')
        return CUSTOM_TIMEZONE

async def day_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('dates_prev_') or query.data.startswith('dates_next_'):
        offset = int(query.data.split('_')[2])
        new_offset = max(0, offset - 7) if 'prev' in query.data else min(14, offset + 7)
        context.user_data['date_offset'] = new_offset
        await query.edit_message_text(f"✅ Часовой пояс: **{context.user_data['timezone']}**\n\n📅 **Выберите день:**", parse_mode='Markdown', reply_markup=get_days_keyboard(new_offset))
        return DAY
    elif query.data == 'back_to_timezone':
        await query.message.reply_text("🌍 **Выберите ваш часовой пояс:**", parse_mode='Markdown', reply_markup=get_timezone_keyboard())
        return TIMEZONE
    
    date_str = query.data.replace('date_', '')
    selected_date = datetime.fromisoformat(date_str).date()
    context.user_data['date'] = selected_date
    context.user_data['date_formatted'] = format_date(selected_date)
    await query.message.reply_text(f"✅ День: **{format_date(selected_date)}**\n\n🕐 **Выберите время:**", parse_mode='Markdown', reply_markup=get_time_keyboard(selected_date))
    return TIME

async def time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    if query.data == 'back_to_days':
        offset = context.user_data.get('date_offset', 0)
        await query.message.reply_text(f"✅ Часовой пояс: **{context.user_data['timezone']}**\n\n📅 **Выберите день:**", parse_mode='Markdown', reply_markup=get_days_keyboard(offset))
        return DAY
    
    selected_time = query.data.replace('time_', '')
    await query.message.reply_text(
        f"✅ **Заявка принята!**\n\n"
        f"📅 День: **{context.user_data['date_formatted']}**\n"
        f"🕐 Время: **{selected_time}**\n"
        f"🌍 Часовой пояс: **{context.user_data['timezone']}**\n\n"
        f"Александр свяжется с вами для подтверждения! 🎸",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )
    
    username = f"@{user.username}" if user.username else "без username"
    await notify_admin(context,
        f"🎉 *НОВАЯ ЗАЯВКА!*\n\n"
        f"👤 {user.first_name}\n"
        f"🔗 {username}\n"
        f"🆔 `{user.id}`\n\n"
        f"📊 Уровень: {context.user_data.get('level')}\n"
        f"🎸 Инструмент: {context.user_data.get('instrument')}\n\n"
        f"📅 {context.user_data['date_formatted']}\n"
        f"🕐 {selected_time}\n"
        f"🌍 {context.user_data['timezone']}"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Запись отменена.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

# ГЛАВНАЯ ФУНКЦИЯ - ЗДЕСЬ БУДЕТ ДОБАВЛЕНА АДМИНКА В ЧАСТИ 2
# ====================================
# АДМИН-ПАНЕЛЬ - КЛАВИАТУРЫ
# ====================================
def get_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Просмотр расписания", callback_data='admin_view')],
        [InlineKeyboardButton("🚫 Заблокировать время", callback_data='admin_block')],
        [InlineKeyboardButton("✅ Разблокировать время", callback_data='admin_unblock')],
        [InlineKeyboardButton("❌ Закрыть", callback_data='admin_close')]
    ])

def get_block_type_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📆 Постоянно (каждую неделю)", callback_data='block_weekly')],
        [InlineKeyboardButton("📅 На конкретную дату", callback_data='block_specific')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='admin_back')]
    ])

def get_weekday_keyboard():
    keyboard = [[InlineKeyboardButton(day, callback_data=f'wday_{WEEKDAYS_EN[i]}')] for i, day in enumerate(WEEKDAYS_RU)]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='admin_back')])
    return InlineKeyboardMarkup(keyboard)

def get_days_keyboard_admin(offset=0):
    dates = get_available_dates(offset)
    keyboard = []
    for date in dates:
        keyboard.append([InlineKeyboardButton(format_date(date), callback_data=f'adate_{date.isoformat()}')])
    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton("⬅️ Раньше", callback_data=f'adates_prev_{offset}'))
    if offset + 7 <= 14:
        nav.append(InlineKeyboardButton("Позже ➡️", callback_data=f'adates_next_{offset}'))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='admin_back')])
    return InlineKeyboardMarkup(keyboard)

def get_time_select_keyboard(blocked_times=None):
    keyboard = []
    for i in range(0, len(TIME_SLOTS), 2):
        row = []
        slot1 = TIME_SLOTS[i]
        is_blocked1 = blocked_times and slot1 in blocked_times
        row.append(InlineKeyboardButton(f"{'🚫' if is_blocked1 else '✅'} {slot1}", callback_data=f'tsel_{slot1}'))
        if i + 1 < len(TIME_SLOTS):
            slot2 = TIME_SLOTS[i + 1]
            is_blocked2 = blocked_times and slot2 in blocked_times
            row.append(InlineKeyboardButton(f"{'🚫' if is_blocked2 else '✅'} {slot2}", callback_data=f'tsel_{slot2}'))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='admin_back')])
    return InlineKeyboardMarkup(keyboard)

# ====================================
# АДМИН-ПАНЕЛЬ - ОБРАБОТЧИКИ
# ====================================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Нет доступа")
        return ConversationHandler.END
    await update.message.reply_text("🔧 **АДМИН-ПАНЕЛЬ**", parse_mode='Markdown', reply_markup=get_admin_keyboard())
    return ADMIN_MENU

async def admin_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'admin_close':
        await query.message.delete()
        return ConversationHandler.END
    
    elif query.data == 'admin_view':
        text = "📅 **ТЕКУЩЕЕ РАСПИСАНИЕ**\n\n**Постоянно заблокировано:**\n"
        for day, slots in SCHEDULE['weekly_blocked'].items():
            if slots:
                day_ru = WEEKDAYS_RU[WEEKDAYS_EN.index(day)]
                text += f"\n**{day_ru}:**\n" + "\n".join(f"• {s}" for s in slots)
        
        if SCHEDULE['specific_dates']:
            text += "\n\n**Конкретные даты:**\n"
            for date_str, slots in sorted(SCHEDULE['specific_dates'].items()):
                if slots:
                    date = datetime.fromisoformat(date_str).date()
                    text += f"\n**{format_date(date)}:**\n" + "\n".join(f"• {s}" for s in slots)
        
        if not any(SCHEDULE['weekly_blocked'].values()) and not SCHEDULE['specific_dates']:
            text += "\nНет заблокированных слотов"
        
        await query.message.reply_text(text, parse_mode='Markdown', reply_markup=get_admin_keyboard())
        return ADMIN_MENU
    
    elif query.data == 'admin_block':
        await query.message.reply_text("**Тип блокировки:**", parse_mode='Markdown', reply_markup=get_block_type_keyboard())
        return ADMIN_BLOCK_TYPE
    
    elif query.data == 'admin_unblock':
        await query.message.reply_text("**Тип разблокировки:**", parse_mode='Markdown', reply_markup=get_block_type_keyboard())
        return ADMIN_UNBLOCK_TYPE

async def admin_block_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'admin_back':
        await query.message.reply_text("🔧 **АДМИН-ПАНЕЛЬ**", parse_mode='Markdown', reply_markup=get_admin_keyboard())
        return ADMIN_MENU
    
    context.user_data['block_type'] = query.data
    if query.data == 'block_weekly':
        await query.message.reply_text("**Выберите день недели:**", parse_mode='Markdown', reply_markup=get_weekday_keyboard())
    else:
        context.user_data['admin_date_offset'] = 0
        await query.message.reply_text("**Выберите дату:**", parse_mode='Markdown', reply_markup=get_days_keyboard_admin(0))
    return ADMIN_BLOCK_DAY

async def admin_block_day_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'admin_back':
        await query.message.reply_text("**Тип блокировки:**", parse_mode='Markdown', reply_markup=get_block_type_keyboard())
        return ADMIN_BLOCK_TYPE
    
    if query.data.startswith('adates_prev_') or query.data.startswith('adates_next_'):
        offset = int(query.data.split('_')[2])
        new_offset = max(0, offset - 7) if 'prev' in query.data else min(14, offset + 7)
        context.user_data['admin_date_offset'] = new_offset
        await query.edit_message_reply_markup(reply_markup=get_days_keyboard_admin(new_offset))
        return ADMIN_BLOCK_DAY
    
    if query.data.startswith('wday_'):
        weekday = query.data.replace('wday_', '')
        context.user_data['selected_day'] = weekday
        blocked = SCHEDULE['weekly_blocked'].get(weekday, [])
        await query.message.reply_text("**Выберите время для блокировки:**\n🚫 - заблокировано\n✅ - свободно", parse_mode='Markdown', reply_markup=get_time_select_keyboard(blocked))
    else:
        date_str = query.data.replace('adate_', '')
        context.user_data['selected_date'] = date_str
        blocked = SCHEDULE['specific_dates'].get(date_str, [])
        await query.message.reply_text("**Выберите время для блокировки:**\n🚫 - заблокировано\n✅ - свободно", parse_mode='Markdown', reply_markup=get_time_select_keyboard(blocked))
    return ADMIN_BLOCK_TIME

async def admin_block_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'admin_back':
        if context.user_data.get('block_type') == 'block_weekly':
            await query.message.reply_text("**Выберите день недели:**", parse_mode='Markdown', reply_markup=get_weekday_keyboard())
        else:
            offset = context.user_data.get('admin_date_offset', 0)
            await query.message.reply_text("**Выберите дату:**", parse_mode='Markdown', reply_markup=get_days_keyboard_admin(offset))
        return ADMIN_BLOCK_DAY
    
    time_slot = query.data.replace('tsel_', '')
    
    if 'selected_day' in context.user_data:
        weekday = context.user_data['selected_day']
        if weekday not in SCHEDULE['weekly_blocked']:
            SCHEDULE['weekly_blocked'][weekday] = []
        if time_slot not in SCHEDULE['weekly_blocked'][weekday]:
            SCHEDULE['weekly_blocked'][weekday].append(time_slot)
            SCHEDULE['weekly_blocked'][weekday].sort()
            save_schedule(SCHEDULE)
            await query.answer("✅ Заблокировано!")
        else:
            await query.answer("⚠️ Уже заблокировано")
        blocked = SCHEDULE['weekly_blocked'][weekday]
        await query.edit_message_reply_markup(reply_markup=get_time_select_keyboard(blocked))
    else:
        date_str = context.user_data['selected_date']
        if date_str not in SCHEDULE['specific_dates']:
            SCHEDULE['specific_dates'][date_str] = []
        if time_slot not in SCHEDULE['specific_dates'][date_str]:
            SCHEDULE['specific_dates'][date_str].append(time_slot)
            SCHEDULE['specific_dates'][date_str].sort()
            save_schedule(SCHEDULE)
            await query.answer("✅ Заблокировано!")
        else:
            await query.answer("⚠️ Уже заблокировано")
        blocked = SCHEDULE['specific_dates'][date_str]
        await query.edit_message_reply_markup(reply_markup=get_time_select_keyboard(blocked))
    return ADMIN_BLOCK_TIME

async def admin_unblock_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'admin_back':
        await query.message.reply_text("🔧 **АДМИН-ПАНЕЛЬ**", parse_mode='Markdown', reply_markup=get_admin_keyboard())
        return ADMIN_MENU
    
    context.user_data['unblock_type'] = query.data
    if query.data == 'block_weekly':
        await query.message.reply_text("**Выберите день недели:**", parse_mode='Markdown', reply_markup=get_weekday_keyboard())
    else:
        context.user_data['admin_date_offset'] = 0
        await query.message.reply_text("**Выберите дату:**", parse_mode='Markdown', reply_markup=get_days_keyboard_admin(0))
    return ADMIN_UNBLOCK_DAY

async def admin_unblock_day_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'admin_back':
        await query.message.reply_text("**Тип разблокировки:**", parse_mode='Markdown', reply_markup=get_block_type_keyboard())
        return ADMIN_UNBLOCK_TYPE
    
    if query.data.startswith('adates_prev_') or query.data.startswith('adates_next_'):
        offset = int(query.data.split('_')[2])
        new_offset = max(0, offset - 7) if 'prev' in query.data else min(14, offset + 7)
        context.user_data['admin_date_offset'] = new_offset
        await query.edit_message_reply_markup(reply_markup=get_days_keyboard_admin(new_offset))
        return ADMIN_UNBLOCK_DAY
    
    if query.data.startswith('wday_'):
        weekday = query.data.replace('wday_', '')
        context.user_data['selected_day_unblock'] = weekday
        blocked = SCHEDULE['weekly_blocked'].get(weekday, [])
        if not blocked:
            await query.answer("⚠️ Нет заблокированных слотов")
            return ADMIN_UNBLOCK_DAY
        await query.message.reply_text("**Выберите время для разблокировки:**\n🚫 - заблокировано\n✅ - свободно", parse_mode='Markdown', reply_markup=get_time_select_keyboard(blocked))
    else:
        date_str = query.data.replace('adate_', '')
        context.user_data['selected_date_unblock'] = date_str
        blocked = SCHEDULE['specific_dates'].get(date_str, [])
        if not blocked:
            await query.answer("⚠️ Нет заблокированных слотов")
            return ADMIN_UNBLOCK_DAY
        await query.message.reply_text("**Выберите время для разблокировки:**\n🚫 - заблокировано\n✅ - свободно", parse_mode='Markdown', reply_markup=get_time_select_keyboard(blocked))
    return ADMIN_UNBLOCK_TIME

async def admin_unblock_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'admin_back':
        if context.user_data.get('unblock_type') == 'block_weekly':
            await query.message.reply_text("**Выберите день недели:**", parse_mode='Markdown', reply_markup=get_weekday_keyboard())
        else:
            offset = context.user_data.get('admin_date_offset', 0)
            await query.message.reply_text("**Выберите дату:**", parse_mode='Markdown', reply_markup=get_days_keyboard_admin(offset))
        return ADMIN_UNBLOCK_DAY
    
    time_slot = query.data.replace('tsel_', '')
    
    if 'selected_day_unblock' in context.user_data:
        weekday = context.user_data['selected_day_unblock']
        if weekday in SCHEDULE['weekly_blocked'] and time_slot in SCHEDULE['weekly_blocked'][weekday]:
            SCHEDULE['weekly_blocked'][weekday].remove(time_slot)
            if not SCHEDULE['weekly_blocked'][weekday]:
                del SCHEDULE['weekly_blocked'][weekday]
            save_schedule(SCHEDULE)
            await query.answer("✅ Разблокировано!")
        else:
            await query.answer("⚠️ Не было заблокировано")
        
        blocked = SCHEDULE['weekly_blocked'].get(weekday, [])
        if blocked:
            await query.edit_message_reply_markup(reply_markup=get_time_select_keyboard(blocked))
        else:
            await query.message.reply_text("✅ Все слоты разблокированы", reply_markup=get_admin_keyboard())
            return ADMIN_MENU
    else:
        date_str = context.user_data['selected_date_unblock']
        if date_str in SCHEDULE['specific_dates'] and time_slot in SCHEDULE['specific_dates'][date_str]:
            SCHEDULE['specific_dates'][date_str].remove(time_slot)
            if not SCHEDULE['specific_dates'][date_str]:
                del SCHEDULE['specific_dates'][date_str]
            save_schedule(SCHEDULE)
            await query.answer("✅ Разблокировано!")
        else:
            await query.answer("⚠️ Не было заблокировано")
        
        blocked = SCHEDULE['specific_dates'].get(date_str, [])
        if blocked:
            await query.edit_message_reply_markup(reply_markup=get_time_select_keyboard(blocked))
        else:
            await query.message.reply_text("✅ Все слоты разблокированы", reply_markup=get_admin_keyboard())
            return ADMIN_MENU
    return ADMIN_UNBLOCK_TIME

# ====================================
# ГЛАВНАЯ ФУНКЦИЯ - ОБНОВЛЁННАЯ С АДМИНКОЙ
# ====================================
# ====================================
# АДМИН-ПАНЕЛЬ - КЛАВИАТУРЫ (УЛУЧШЕННАЯ ВЕРСИЯ)
# ====================================
def get_admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Просмотр расписания", callback_data='admin_view')],
        [InlineKeyboardButton("⚙️ Управление временем", callback_data='admin_manage')],
        [InlineKeyboardButton("❌ Закрыть", callback_data='admin_close')]
    ])

def get_manage_type_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📆 Постоянно (каждую неделю)", callback_data='manage_weekly')],
        [InlineKeyboardButton("📅 На конкретную дату", callback_data='manage_specific')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='admin_back')]
    ])

def get_weekday_keyboard():
    keyboard = [[InlineKeyboardButton(day, callback_data=f'wday_{WEEKDAYS_EN[i]}')] for i, day in enumerate(WEEKDAYS_RU)]
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='admin_back')])
    return InlineKeyboardMarkup(keyboard)

def get_days_keyboard_admin(offset=0):
    dates = get_available_dates(offset)
    keyboard = []
    for date in dates:
        keyboard.append([InlineKeyboardButton(format_date(date), callback_data=f'adate_{date.isoformat()}')])
    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton("⬅️ Раньше", callback_data=f'adates_prev_{offset}'))
    if offset + 7 <= 14:
        nav.append(InlineKeyboardButton("Позже ➡️", callback_data=f'adates_next_{offset}'))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='admin_back')])
    return InlineKeyboardMarkup(keyboard)

def get_time_toggle_keyboard(blocked_times=None):
    """Клавиатура с переключением блок/разблок одной кнопкой"""
    keyboard = []
    for i in range(0, len(TIME_SLOTS), 2):
        row = []
        slot1 = TIME_SLOTS[i]
        is_blocked1 = blocked_times and slot1 in blocked_times
        row.append(InlineKeyboardButton(
            f"{'🚫' if is_blocked1 else '✅'} {slot1}",
            callback_data=f'toggle_{slot1}'
        ))
        if i + 1 < len(TIME_SLOTS):
            slot2 = TIME_SLOTS[i + 1]
            is_blocked2 = blocked_times and slot2 in blocked_times
            row.append(InlineKeyboardButton(
                f"{'🚫' if is_blocked2 else '✅'} {slot2}",
                callback_data=f'toggle_{slot2}'
            ))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data='admin_done')])
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='admin_back')])
    return InlineKeyboardMarkup(keyboard)

# ====================================
# АДМИН-ПАНЕЛЬ - ОБРАБОТЧИКИ (УЛУЧШЕННАЯ ВЕРСИЯ)
# ====================================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Нет доступа")
        return ConversationHandler.END
    await update.message.reply_text("🔧 **АДМИН-ПАНЕЛЬ**", parse_mode='Markdown', reply_markup=get_admin_keyboard())
    return ADMIN_MENU

async def admin_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'admin_close':
        await query.message.delete()
        return ConversationHandler.END
    
    elif query.data == 'admin_view':
        text = "📅 **ТЕКУЩЕЕ РАСПИСАНИЕ**\n\n**Постоянно заблокировано:**\n"
        has_content = False
        
        for day, slots in SCHEDULE['weekly_blocked'].items():
            if slots:
                has_content = True
                day_ru = WEEKDAYS_RU[WEEKDAYS_EN.index(day)]
                text += f"\n**{day_ru}:**\n" + "\n".join(f"• {s}" for s in slots)
        
        if SCHEDULE['specific_dates']:
            has_content = True
            text += "\n\n**Конкретные даты:**\n"
            for date_str, slots in sorted(SCHEDULE['specific_dates'].items()):
                if slots:
                    date = datetime.fromisoformat(date_str).date()
                    text += f"\n**{format_date(date)}:**\n" + "\n".join(f"• {s}" for s in slots)
        
        if not has_content:
            text += "\n\nНет заблокированных слотов"
        
        await query.message.reply_text(text, parse_mode='Markdown', reply_markup=get_admin_keyboard())
        return ADMIN_MENU
    
    elif query.data == 'admin_manage':
        await query.message.reply_text("**Выберите тип управления:**", parse_mode='Markdown', reply_markup=get_manage_type_keyboard())
        return ADMIN_BLOCK_TYPE

async def admin_manage_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'admin_back':
        await query.message.reply_text("🔧 **АДМИН-ПАНЕЛЬ**", parse_mode='Markdown', reply_markup=get_admin_keyboard())
        return ADMIN_MENU
    
    context.user_data['manage_type'] = query.data
    
    if query.data == 'manage_weekly':
        await query.message.reply_text("**Выберите день недели:**", parse_mode='Markdown', reply_markup=get_weekday_keyboard())
    else:
        context.user_data['admin_date_offset'] = 0
        await query.message.reply_text("**Выберите дату:**", parse_mode='Markdown', reply_markup=get_days_keyboard_admin(0))
    
    return ADMIN_BLOCK_DAY

async def admin_manage_day_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'admin_back':
        await query.message.reply_text("**Выберите тип управления:**", parse_mode='Markdown', reply_markup=get_manage_type_keyboard())
        return ADMIN_BLOCK_TYPE
    
    if query.data.startswith('adates_prev_') or query.data.startswith('adates_next_'):
        offset = int(query.data.split('_')[2])
        new_offset = max(0, offset - 7) if 'prev' in query.data else min(14, offset + 7)
        context.user_data['admin_date_offset'] = new_offset
        await query.edit_message_reply_markup(reply_markup=get_days_keyboard_admin(new_offset))
        return ADMIN_BLOCK_DAY
    
    if query.data.startswith('wday_'):
        weekday = query.data.replace('wday_', '')
        context.user_data['selected_day'] = weekday
        context.user_data.pop('selected_date', None)  # Очищаем дату если была
        blocked = SCHEDULE['weekly_blocked'].get(weekday, [])
        day_ru = WEEKDAYS_RU[WEEKDAYS_EN.index(weekday)]
        await query.message.reply_text(
            f"**Управление временем: {day_ru}**\n\n"
            "🚫 - Заблокировано\n"
            "✅ - Свободно\n\n"
            "*Нажмите на время для переключения*",
            parse_mode='Markdown',
            reply_markup=get_time_toggle_keyboard(blocked)
        )
    else:
        date_str = query.data.replace('adate_', '')
        context.user_data['selected_date'] = date_str
        context.user_data.pop('selected_day', None)  # Очищаем день если был
        blocked = SCHEDULE['specific_dates'].get(date_str, [])
        date = datetime.fromisoformat(date_str).date()
        await query.message.reply_text(
            f"**Управление временем: {format_date(date)}**\n\n"
            "🚫 - Заблокировано\n"
            "✅ - Свободно\n\n"
            "*Нажмите на время для переключения*",
            parse_mode='Markdown',
            reply_markup=get_time_toggle_keyboard(blocked)
        )
    
    return ADMIN_BLOCK_TIME

async def admin_toggle_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.data == 'admin_back':
        await query.answer()
        if context.user_data.get('manage_type') == 'manage_weekly':
            await query.message.reply_text("**Выберите день недели:**", parse_mode='Markdown', reply_markup=get_weekday_keyboard())
        else:
            offset = context.user_data.get('admin_date_offset', 0)
            await query.message.reply_text("**Выберите дату:**", parse_mode='Markdown', reply_markup=get_days_keyboard_admin(offset))
        return ADMIN_BLOCK_DAY
    
    if query.data == 'admin_done':
        await query.answer("✅ Изменения сохранены!")
        await query.message.reply_text("🔧 **АДМИН-ПАНЕЛЬ**", parse_mode='Markdown', reply_markup=get_admin_keyboard())
        return ADMIN_MENU
    
    # Переключение состояния времени
    time_slot = query.data.replace('toggle_', '')
    
    if 'selected_day' in context.user_data:
        weekday = context.user_data['selected_day']
        if weekday not in SCHEDULE['weekly_blocked']:
            SCHEDULE['weekly_blocked'][weekday] = []
        
        if time_slot in SCHEDULE['weekly_blocked'][weekday]:
            # Разблокировать
            SCHEDULE['weekly_blocked'][weekday].remove(time_slot)
            if not SCHEDULE['weekly_blocked'][weekday]:
                del SCHEDULE['weekly_blocked'][weekday]
            save_schedule(SCHEDULE)
            await query.answer("✅ Разблокировано!")
        else:
            # Заблокировать
            SCHEDULE['weekly_blocked'][weekday].append(time_slot)
            SCHEDULE['weekly_blocked'][weekday].sort()
            save_schedule(SCHEDULE)
            await query.answer("🚫 Заблокировано!")
        
        blocked = SCHEDULE['weekly_blocked'].get(weekday, [])
        await query.edit_message_reply_markup(reply_markup=get_time_toggle_keyboard(blocked))
    
    else:
        date_str = context.user_data['selected_date']
        if date_str not in SCHEDULE['specific_dates']:
            SCHEDULE['specific_dates'][date_str] = []
        
        if time_slot in SCHEDULE['specific_dates'][date_str]:
            # Разблокировать
            SCHEDULE['specific_dates'][date_str].remove(time_slot)
            if not SCHEDULE['specific_dates'][date_str]:
                del SCHEDULE['specific_dates'][date_str]
            save_schedule(SCHEDULE)
            await query.answer("✅ Разблокировано!")
        else:
            # Заблокировать
            SCHEDULE['specific_dates'][date_str].append(time_slot)
            SCHEDULE['specific_dates'][date_str].sort()
            save_schedule(SCHEDULE)
            await query.answer("🚫 Заблокировано!")
        
        blocked = SCHEDULE['specific_dates'].get(date_str, [])
        await query.edit_message_reply_markup(reply_markup=get_time_toggle_keyboard(blocked))
    
    return ADMIN_BLOCK_TIME

# ====================================
# ГЛАВНАЯ ФУНКЦИЯ - С УЛУЧШЕННОЙ АДМИНКОЙ
# ====================================
def main():
    application = Application.builder().token(TOKEN).build()
    
    # ConversationHandler для записи
    booking_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern='^start_booking$')],
        states={
            LEVEL: [CallbackQueryHandler(level_handler)],
            INSTRUMENT: [CallbackQueryHandler(instrument_handler)],
            TIMEZONE: [CallbackQueryHandler(timezone_handler)],
            CUSTOM_TIMEZONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_timezone_handler)],
            DAY: [CallbackQueryHandler(day_handler)],
            TIME: [CallbackQueryHandler(time_handler)],
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(button_handler, pattern='^back_to_main$'),
            CallbackQueryHandler(button_handler, pattern='^trial$')
        ],
    )
    
    # ConversationHandler для админ-панели (УЛУЧШЕННАЯ ВЕРСИЯ)
    admin_conv = ConversationHandler(
        entry_points=[CommandHandler('admin', admin_panel)],
        states={
            ADMIN_MENU: [CallbackQueryHandler(admin_menu_handler)],
            ADMIN_BLOCK_TYPE: [CallbackQueryHandler(admin_manage_type_handler)],
            ADMIN_BLOCK_DAY: [CallbackQueryHandler(admin_manage_day_handler)],
            ADMIN_BLOCK_TIME: [CallbackQueryHandler(admin_toggle_time_handler)],
        },
        fallbacks=[CommandHandler('admin', admin_panel)],
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(booking_conv)
    application.add_handler(admin_conv)
    application.add_handler(CallbackQueryHandler(button_handler))
    
    logger.info("🚀 Бот запущен с улучшенной админ-панелью!")
    application.run_polling()

if __name__ == '__main__':
    main()
