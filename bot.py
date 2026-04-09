# -*- coding: utf-8 -*-
import os, json, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8571836508:AAHtkblRtS4eiBzQwvY6R4QYFukYRScuTsM")
SET_SQUAT, SET_BENCH, SET_DEADLIFT = range(3)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "all_weeks.json"), "r", encoding="utf-8") as f:
    WEEKS = json.load(f)
with open(os.path.join(BASE_DIR, "program_meta.json"), "r", encoding="utf-8") as f:
    META = json.load(f)
DAYS_ORDER = ["ПН", "ВТ", "ЧТ", "ПТ"]
DAY_NAMES = {"ПН": "Понедельник", "ВТ": "Вторник", "ЧТ": "Четверг", "ПТ": "Пятница"}
user_data = {}
def load_user(uid):
    if uid not in user_data:
        user_data[uid] = {"squats": None, "bench": None, "deadlift": None}
    return user_data[uid]
def save_user(uid, data):
    user_data[uid] = data

def format_exercise(ex):
    name = ex["name"]
    sets = ex["sets"]
    reps = ex["reps"]
    intensity = ex["intensity"]
    if sets == "" and reps == "":
        return name
    line = name + chr(10) + "    " + str(sets) + " x " + str(reps)
    if intensity:
        line += " | " + intensity
    return line

def format_day(week_num, day_key):
    week = WEEKS[str(week_num)]
    day = week[day_key]
    block = week["block"]
    msg = "*Nedelya " + str(week_num) + " | " + block + "*" + chr(10)*2
    msg += "*" + DAY_NAMES.get(day_key, day_key) + "*" + chr(10)
    msg += "_" + day["title"] + "_" + chr(10)*2
    msg += "Razminka: " + META["warmup"] + chr(10)
    msg += "Otdih: " + META["rest_main"] + " (glavnie), " + META["rest_acc"] + " (vspomogatelnie)" + chr(10)*2
    for ex in day["exercises"]:
        msg += format_exercise(ex) + chr(10)*2
    return msg
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for wn in range(1, 13):
        block = META["blocks"].get(wn, "")
        keyboard.append([InlineKeyboardButton("Nedelya " + str(wn) + " - " + block, callback_data="week_" + str(wn))])
    keyboard.append([InlineKeyboardButton("Kalkulyator 1RM", callback_data="calc_1rm")])
    keyboard.append([InlineKeyboardButton("Moi maksimumy", callback_data="show_max")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("GIPERSILA v3.0" + chr(10)*2 + "Vyberi nedelyu i den treningi:", reply_markup=reply_markup)

async def week_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    week_num = int(query.data.split("_")[1])
    keyboard = []
    for dk in DAYS_ORDER:
        day_data = WEEKS[str(week_num)][dk]
        t = day_data["title"]
        keyboard.append([InlineKeyboardButton(DAY_NAMES[dk] + ": " + t, callback_data="day_" + str(week_num) + "_" + dk)])
    keyboard.append([InlineKeyboardButton("Nazad k nedelyam", callback_data="back_to_weeks")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Nedelya " + str(week_num) + ". Vyberi den treningi:", reply_markup=reply_markup)

async def day_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    week_num = int(parts[1])
    day_key = parts[2]
    msg = format_day(week_num, day_key)
    keyboard = [[InlineKeyboardButton("Nazad k dnyam", callback_data="week_" + str(week_num))],
                [InlineKeyboardButton("Glavnoe menyu", callback_data="back_to_weeks")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

async def back_to_weeks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = []
    for wn in range(1, 13):
        block = META["blocks"].get(wn, "")
        keyboard.append([InlineKeyboardButton("Nedelya " + str(wn) + " - " + block, callback_data="week_" + str(wn))])
    keyboard.append([InlineKeyboardButton("Kalkulyator 1RM", callback_data="calc_1rm")])
    keyboard.append([InlineKeyboardButton("Moi maksimumy", callback_data="show_max")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("GIPERSILA v3.0" + chr(10)*2 + "Vyberi nedelyu i den treningi:", reply_markup=reply_markup)
async def calc_1rm_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Kalkulyator 1RM" + chr(10)*2 + "Vvedes ves i povtoreniya dlya PRISEDA:" + chr(10) + "Format: ves x povtoreniya" + chr(10) + "Primer: 140 x 5" + chr(10)*2 + "Ili /skip propustit.")
    return SET_SQUAT

async def set_squats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_lift(update, context, "squats", SET_BENCH, "ZHIME LYOGHA")

async def set_bench(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_lift(update, context, "bench", SET_DEADLIFT, "SUMO-TYAGE")

async def set_deadlift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await process_lift(update, context, "deadlift", ConversationHandler.END, None)

async def process_lift(update, context, lift_name, next_state, next_lift_name):
    text = update.message.text.strip()
    if text.lower() == "/skip":
        if next_state == ConversationHandler.END:
            return await show_1rm_results(update, context)
        await update.message.reply_text("Propushcheno." + chr(10)*2 + "Vvedes dlya " + next_lift_name + ":")
        return next_state
    try:
        parts = text.split("x")
        weight = float(parts[0].strip())
        reps = int(parts[1].strip())
        if reps == 1:
            one_rm = weight
        else:
            one_rm = weight * (1 + reps / 30)
        one_rm = round(one_rm, 1)
        context.user_data[lift_name] = one_rm
        names = {"squats": "Prised", "bench": "Zhim", "deadlift": "Sumo"}
        if next_state == ConversationHandler.END:
            return await show_1rm_results(update, context)
        await update.message.reply_text(names[lift_name] + ": " + str(one_rm) + " kg" + chr(10)*2 + "Vvedes dlya " + next_lift_name + ":")
        return next_state
    except (ValueError, IndexError):
        await update.message.reply_text("Neverniy format. Primer: 140 x 5")
        return next_state if next_state != ConversationHandler.END else SET_SQUAT

async def show_1rm_results(update, context):
    user_id = update.effective_user.id
    ud = load_user(user_id)
    for k, v in context.user_data.items():
        if k in ("squats", "bench", "deadlift"):
            ud[k] = v
    save_user(user_id, ud)
    msg = "Tvoi raschetnie 1RM:" + chr(10)*2
    names = {"squats": "Prised", "bench": "Zhim lyogha", "deadlift": "Sumo-tyaga"}
    for k, label in names.items():
        val = ud.get(k)
        if val:
            msg += label + ": " + str(val) + " kg" + chr(10)
        else:
            msg += label + ": ne ukazano" + chr(10)
    keyboard = [[InlineKeyboardButton("Glavnoe menyu", callback_data="back_to_weeks")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(msg, reply_markup=reply_markup)
    return ConversationHandler.END

async def show_max(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    ud = load_user(user_id)
    msg = "Tvoi tekushchie 1RM:" + chr(10)*2
    names = {"squats": "Prised", "bench": "Zhim lyogha", "deadlift": "Sumo-tyaga"}
    for k, label in names.items():
        val = ud.get(k)
        if val:
            msg += label + ": " + str(val) + " kg" + chr(10)
        else:
            msg += label + ": ne ukazano" + chr(10)
    msg += chr(10) + "Dlya obnovleniya: nakhmi Kalkulyator 1RM"
    keyboard = [[InlineKeyboardButton("Glavnoe menyu", callback_data="back_to_weeks")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(msg, reply_markup=reply_markup)
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("calc", calc_1rm_start))
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(calc_1rm_start, pattern="^calc_1rm$")],
        states={
            SET_SQUAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_squats)],
            SET_BENCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_bench)],
            SET_DEADLIFT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_deadlift)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
    )
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(week_selected, pattern="^week_[0-9]+$"))
    app.add_handler(CallbackQueryHandler(day_selected, pattern="^day_[0-9]+_"))
    app.add_handler(CallbackQueryHandler(back_to_weeks, pattern="^back_to_weeks$"))
    app.add_handler(CallbackQueryHandler(show_max, pattern="^show_max$"))
    logger.info("Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()