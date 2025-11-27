import logging
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
ADMIN_ID = 5094488507
SCHEDULE_FILE = 'schedule.json'

# Состояния админ-панели
ADMIN_MENU, ADMIN_BLOCK_TYPE, ADMIN_BLOCK_DAY, ADMIN_BLOCK_TIME = range(4)
ADMIN_UNBLOCK_TYPE, ADMIN_UNBLOCK_DAY, ADMIN_UNBLOCK_TIME = range(4, 7)

WEEKDAYS_RU = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
WEEKDAYS_EN = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
MONTHS_RU = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']

TIME_SLOTS = ['12:00-13:00', '13:00-14:00', '14:00-15:00', '15:00-16:00', '16:00-17:00', 
              '17:00-18:00', '18:00-19:00', '19:00-20:00', '20:00-21:00', '21:00-22:00', '22:00-23:00']

def load_schedule():
    try:
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {'weekly_blocked': {}, 'specific_dates': {}}

def save_schedule(schedule):
    with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

def format_date(date):
    return f"{WEEKDAYS_RU[date.weekday()]} {date.day} {MONTHS_RU[date.month - 1]}"

def get_available_dates(offset=0):
    dates = []
    start_date = datetime.now().date() + timedelta(days=offset)
    for i in range(7):
        date = start_date + timedelta(days=i)
        if (date - datetime.now().date()).days <= 14:
            dates.append(date)
    return dates

# Клавиатуры админ-панели
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
    if offset > 0: nav.append(InlineKeyboardButton("⬅️ Раньше", callback_data=f'adates_prev_{offset}'))
    if offset + 7 <= 14: nav.append(InlineKeyboardButton("Позже ➡️", callback_data=f'adates_next_{offset}'))
    if nav: keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='admin_back')])
    return InlineKeyboardMarkup(keyboard)

def get_time_select_keyboard(blocked_times=None):
    keyboard = []
    for i in range(0, len(TIME_SLOTS), 2):
        row = []
        slot1 = TIME_SLOTS[i]
        is_blocked1 = blocked_times and slot1 in blocked_times
        row.append(InlineKeyboardButton(
            f"{'🚫' if is_blocked1 else '✅'} {slot1}",
            callback_data=f'tsel_{slot1}'
        ))
        if i + 1 < len(TIME_SLOTS):
            slot2 = TIME_SLOTS[i + 1]
            is_blocked2 = blocked_times and slot2 in blocked_times
            row.append(InlineKeyboardButton(
                f"{'🚫' if is_blocked2 else '✅'} {slot2}",
                callback_data=f'tsel_{slot2}'
            ))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='admin_back')])
    return InlineKeyboardMarkup(keyboard)

# Обработчики админ-панели
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
        schedule = load_schedule()
        text = "📅 **ТЕКУЩЕЕ РАСПИСАНИЕ**\n\n**Постоянно заблокировано:**\n"
        
        for day, slots in schedule['weekly_blocked'].items():
            if slots:
                day_ru = WEEKDAYS_RU[WEEKDAYS_EN.index(day)]
                text += f"\n**{day_ru}:**\n" + "\n".join(f"• {s}" for s in slots)
        
        if schedule['specific_dates']:
            text += "\n\n**Конкретные даты:**\n"
            for date_str, slots in sorted(schedule['specific_dates'].items()):
                if slots:
                    date = datetime.fromisoformat(date_str).date()
                    text += f"\n**{format_date(date)}:**\n" + "\n".join(f"• {s}" for s in slots)
        
        if not schedule['weekly_blocked'] and not schedule['specific_dates']:
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
    
    schedule = load_schedule()
    
    if query.data.startswith('wday_'):
        weekday = query.data.replace('wday_', '')
        context.user_data['selected_day'] = weekday
        blocked = schedule['weekly_blocked'].get(weekday, [])
        await query.message.reply_text(f"**Выберите время для блокировки:**\n🚫 - заблокировано\n✅ - свободно",
                                      parse_mode='Markdown', reply_markup=get_time_select_keyboard(blocked))
    else:
        date_str = query.data.replace('adate_', '')
        context.user_data['selected_date'] = date_str
        blocked = schedule['specific_dates'].get(date_str, [])
        await query.message.reply_text(f"**Выберите время для блокировки:**\n🚫 - заблокировано\n✅ - свободно",
                                      parse_mode='Markdown', reply_markup=get_time_select_keyboard(blocked))
    
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
    schedule = load_schedule()
    
    if 'selected_day' in context.user_data:
        weekday = context.user_data['selected_day']
        if weekday not in schedule['weekly_blocked']:
            schedule['weekly_blocked'][weekday] = []
        if time_slot not in schedule['weekly_blocked'][weekday]:
            schedule['weekly_blocked'][weekday].append(time_slot)
            schedule['weekly_blocked'][weekday].sort()
            save_schedule(schedule)
            await query.answer("✅ Заблокировано!")
        else:
            await query.answer("⚠️ Уже заблокировано")
        
        blocked = schedule['weekly_blocked'][weekday]
        await query.edit_message_reply_markup(reply_markup=get_time_select_keyboard(blocked))
    else:
        date_str = context.user_data['selected_date']
        if date_str not in schedule['specific_dates']:
            schedule['specific_dates'][date_str] = []
        if time_slot not in schedule['specific_dates'][date_str]:
            schedule['specific_dates'][date_str].append(time_slot)
            schedule['specific_dates'][date_str].sort()
            save_schedule(schedule)
            await query.answer("✅ Заблокировано!")
        else:
            await query.answer("⚠️ Уже заблокировано")
        
        blocked = schedule['specific_dates'][date_str]
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
    
    schedule = load_schedule()
    
    if query.data.startswith('wday_'):
        weekday = query.data.replace('wday_', '')
        context.user_data['selected_day_unblock'] = weekday
        blocked = schedule['weekly_blocked'].get(weekday, [])
        if not blocked:
            await query.answer("⚠️ Нет заблокированных слотов")
            return ADMIN_UNBLOCK_DAY
        await query.message.reply_text(f"**Выберите время для разблокировки:**\n🚫 - заблокировано\n✅ - свободно",
                                      parse_mode='Markdown', reply_markup=get_time_select_keyboard(blocked))
    else:
        date_str = query.data.replace('adate_', '')
        context.user_data['selected_date_unblock'] = date_str
        blocked = schedule['specific_dates'].get(date_str, [])
        if not blocked:
            await query.answer("⚠️ Нет заблокированных слотов")
            return ADMIN_UNBLOCK_DAY
        await query.message.reply_text(f"**Выберите время для разблокировки:**\n🚫 - заблокировано\n✅ - свободно",
                                      parse_mode='Markdown', reply_markup=get_time_select_keyboard(blocked))
    
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
    schedule = load_schedule()
    
    if 'selected_day_unblock' in context.user_data:
        weekday = context.user_data['selected_day_unblock']
        if weekday in schedule['weekly_blocked'] and time_slot in schedule['weekly_blocked'][weekday]:
            schedule['weekly_blocked'][weekday].remove(time_slot)
            if not schedule['weekly_blocked'][weekday]:
                del schedule['weekly_blocked'][weekday]
            save_schedule(schedule)
            await query.answer("✅ Разблокировано!")
        else:
            await query.answer("⚠️ Не было заблокировано")
        
        blocked = schedule['weekly_blocked'].get(weekday, [])
        if blocked:
            await query.edit_message_reply_markup(reply_markup=get_time_select_keyboard(blocked))
        else:
            await query.message.reply_text("✅ Все слоты разблокированы", reply_markup=get_admin_keyboard())
            return ADMIN_MENU
    else:
        date_str = context.user_data['selected_date_unblock']
        if date_str in schedule['specific_dates'] and time_slot in schedule['specific_dates'][date_str]:
            schedule['specific_dates'][date_str].remove(time_slot)
            if not schedule['specific_dates'][date_str]:
                del schedule['specific_dates'][date_str]
            save_schedule(schedule)
            await query.answer("✅ Разблокировано!")
        else:
            await query.answer("⚠️ Не было заблокировано")
        
        blocked = schedule['specific_dates'].get(date_str, [])
        if blocked:
            await query.edit_message_reply_markup(reply_markup=get_time_select_keyboard(blocked))
        else:
            await query.message.reply_text("✅ Все слоты разблокированы", reply_markup=get_admin_keyboard())
            return ADMIN_MENU
    
    return ADMIN_UNBLOCK_TIME

def main():
    application = Application.builder().token(TOKEN).build()
    
    # ConversationHandler для админ-панели
    admin_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('admin', admin_panel)],
        states={
            ADMIN_MENU: [CallbackQueryHandler(admin_menu_handler)],
            ADMIN_BLOCK_TYPE: [CallbackQueryHandler(admin_block_type_handler)],
            ADMIN_BLOCK_DAY: [CallbackQueryHandler(admin_block_day_handler)],
            ADMIN_BLOCK_TIME: [CallbackQueryHandler(admin_block_time_handler)],
            ADMIN_UNBLOCK_TYPE: [CallbackQueryHandler(admin_unblock_type_handler)],
            ADMIN_UNBLOCK_DAY: [CallbackQueryHandler(admin_unblock_day_handler)],
            ADMIN_UNBLOCK_TIME: [CallbackQueryHandler(admin_unblock_time_handler)],
        },
        fallbacks=[CommandHandler('admin', admin_panel)],
    )
    
    application.add_handler(admin_conv_handler)
    
    logger.info("Админ-панель загружена...")
    application.run_polling()

if __name__ == '__main__':
    main()
