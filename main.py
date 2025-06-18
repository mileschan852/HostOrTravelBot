import os
import logging
from datetime import datetime
from telegram import (
    Update, 
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)
from database import init_db, add_party, get_upcoming_parties, delete_expired_events
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Load env vars
BOT_TOKEN = os.getenv('BOT_TOKEN')
MTR_STATIONS = [
    "Admiralty", "Airport", "Causeway Bay", "Central", "Chai Wan", 
    "Kowloon Tong", "Mong Kok", "Tsim Sha Tsui", "Tsuen Wan", "Yuen Long"
]

# States
HOSTING, START_TIME, END_TIME, COST, AREA = range(5)

# Initialize
init_db()
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, "Welcome to HostOrTravelBot!")

async def show_main_menu(update, text):
    keyboard = [["Refresh", "Host"]]
    await update.message.reply_text(
        text,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    await list_parties(update)

async def list_parties(update):
    parties = get_upcoming_parties()
    if not parties:
        await update.message.reply_text("No upcoming parties 🎉")
        return
    
    for party in parties:
        _, username, start, end, cost, area = party
        message = (
            f"🎉 Host: @{username}\n"
            f"🕒 Time: {start.strftime('%d %b %H:%M')} - {end.strftime('%H:%M')}\n"
            f"💵 Cost: {cost} TON\n"
            f"📍 Area: {area}\n"
        )
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Message Host", url=f"tg://user?id={username}")]
            ])
        )

async def start_hosting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Let's host a party! Enter START time (YYYY-MM-DD HH:MM):",
        reply_markup=ReplyKeyboardRemove()
    )
    return START_TIME

async def set_start_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['start_time'] = datetime.strptime(update.message.text, '%Y-%m-%d %H:%M')
        await update.message.reply_text("Enter END time (YYYY-MM-DD HH:MM):")
        return END_TIME
    except ValueError:
        await update.message.reply_text("Invalid format! Use YYYY-MM-DD HH:MM")
        return START_TIME

async def set_end_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        end_time = datetime.strptime(update.message.text, '%Y-%m-%d %H:%M')
        if end_time <= context.user_data['start_time']:
            await update.message.reply_text("End time must be AFTER start time!")
            return END_TIME
            
        context.user_data['end_time'] = end_time
        await update.message.reply_text("Enter COST per head (TON):")
        return COST
    except ValueError:
        await update.message.reply_text("Invalid format! Use YYYY-MM-DD HH:MM")
        return END_TIME

async def set_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        cost = float(update.message.text)
        if cost < 0:
            await update.message.reply_text("Cost must be positive!")
            return COST
            
        context.user_data['cost'] = cost
        keyboard = [[station] for station in MTR_STATIONS]
        await update.message.reply_text(
            "Select AREA:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        return AREA
    except ValueError:
        await update.message.reply_text("Invalid number! Enter digits only")
        return COST

async def set_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    area = update.message.text
    if area not in MTR_STATIONS:
        await update.message.reply_text("Select from the list!")
        return AREA
        
    # Save party
    add_party(
        host_id=update.message.from_user.id,
        host_username=update.message.from_user.username,
        start_time=context.user_data['start_time'],
        end_time=context.user_data['end_time'],
        cost=context.user_data['cost'],
        area=area
    )
    
    await update.message.reply_text("Party listed successfully! ✅")
    await show_main_menu(update, "Main Menu")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, "Operation cancelled")
    return ConversationHandler.END

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    delete_expired_events()
    await show_main_menu(update, "List refreshed ✅")

async def auto_cleanup(context: ContextTypes.DEFAULT_TYPE):
    delete_expired_events()

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Schedule cleanup every hour
    scheduler = AsyncIOScheduler()
    scheduler.add_job(auto_cleanup, 'interval', hours=1)
    scheduler.start()
    
    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Host$"), start_hosting)],
        states={
            START_TIME: [MessageHandler(filters.TEXT, set_start_time)],
            END_TIME: [MessageHandler(filters.TEXT, set_end_time)],
            COST: [MessageHandler(filters.TEXT, set_cost)],
            AREA: [MessageHandler(filters.TEXT, set_area)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^Refresh$"), refresh))
    application.add_handler(conv_handler)
    
    application.run_polling()

if __name__ == "__main__":
    main()