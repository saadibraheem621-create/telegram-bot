import os
import json
import random
import string
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "8586159632:AAF6aWV9g7kNWkpCVsRE5iy08_SUpFKtj68"
ADMIN_CHAT_ID = "PUT_YOUR_TELEGRAM_CHAT_ID_HERE"

ORDERS_FILE = "orders.json"
PRO_CODES_FILE = "pro_codes.json"

user_states = {}


# =========================
# JSON helpers
# =========================
def load_json_file(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_orders():
    return load_json_file(ORDERS_FILE, [])


def save_orders(orders):
    save_json_file(ORDERS_FILE, orders)


def load_pro_codes():
    return load_json_file(PRO_CODES_FILE, {})


def save_pro_codes(codes):
    save_json_file(PRO_CODES_FILE, codes)


def is_admin(user_id):
    return str(user_id) == str(ADMIN_CHAT_ID)


# =========================
# Orders / codes
# =========================
def add_order(order):
    orders = load_orders()
    orders.append(order)
    save_orders(orders)


def generate_pro_code(length=6):
    chars = string.ascii_uppercase + string.digits
    pro_codes = load_pro_codes()

    while True:
        code = "PRO-" + "".join(random.choices(chars, k=length))
        if code not in pro_codes:
            return code


def create_pro_code_for_user(name, days_valid=30, max_uses=1):
    code = generate_pro_code()
    expires_date = (datetime.now() + timedelta(days=days_valid)).strftime("%Y-%m-%d")

    pro_codes = load_pro_codes()
    pro_codes[code] = {
        "name": name,
        "expires": expires_date,
        "used": False,
        "max_uses": max_uses,
        "created_at": datetime.now().isoformat(),
    }
    save_pro_codes(pro_codes)

    return code, expires_date


# =========================
# User flow
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_states[user_id] = {"step": "email"}

    await update.message.reply_text(
        "أهلاً 👋\n"
        "أرسل إيميلك حتى نكمل الطلب."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update.effective_user.id):
        text = (
            "أوامر الأدمن:\n\n"
            "/orders - عرض آخر الطلبات\n"
            "/pending - عرض الطلبات المعلقة\n"
            "/approve USER_ID - موافقة وتوليد كود\n"
            "/reject USER_ID - رفض الطلب\n"
            "/generate NAME DAYS MAX_USES - توليد كود يدوي\n"
            "/codes - عرض آخر الأكواد\n"
            "/deletecode CODE - حذف كود\n"
        )
    else:
        text = (
            "الأوامر:\n\n"
            "/start - بدء الطلب\n"
        )

    await update.message.reply_text(text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in user_states:
        await update.message.reply_text("اكتب /start حتى نبدأ.")
        return

    state = user_states[user_id]

    if state["step"] == "email":
        state["email"] = text
        state["step"] = "payment_screenshot"
        await update.message.reply_text(
            "تمام ✅\n"
            "هسه أرسل صورة إثبات الدفع."
        )
        return

    if state["step"] == "done":
        await update.message.reply_text("طلبك مسجل بالفعل ✅")
        return

    await update.message.reply_text("أرسل /start حتى نبدأ من جديد.")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in user_states:
        await update.message.reply_text("اكتب /start حتى نبدأ.")
        return

    state = user_states[user_id]

    if state.get("step") != "payment_screenshot":
        await update.message.reply_text("أرسل /start حتى نبدأ.")
        return

    photo = update.message.photo[-1]
    file_id = photo.file_id

    order = {
        "user_id": user_id,
        "username": update.effective_user.username,
        "name": update.effective_user.full_name,
        "email": state.get("email", ""),
        "file_id": file_id,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }

    add_order(order)
    state["step"] = "done"

    await update.message.reply_text(
        "تم استلام طلبك ✅\n"
        "راح نراجعه ونرسل لك كود التفعيل قريباً."
    )

    admin_text = (
        "📥 طلب جديد\n\n"
        f"الاسم: {order['name']}\n"
        f"اليوزر: @{order['username']}\n"
        f"الإيميل: {order['email']}\n"
        f"User ID: {order['user_id']}\n"
        f"الوقت: {order['created_at']}"
    )

    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)
    await context.bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=file_id)


# =========================
# Admin commands
# =========================
async def orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("هذا الأمر للأدمن فقط.")
        return

    orders_data = load_orders()

    if not orders_data:
        await update.message.reply_text("ماكو طلبات حالياً.")
        return

    text = "📋 آخر الطلبات:\n\n"
    for i, order in enumerate(orders_data[-10:], start=1):
        text += (
            f"{i}. {order['name']} | {order['email']} | "
            f"{order['status']} | {order['user_id']}\n"
        )

    await update.message.reply_text(text)


async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("هذا الأمر للأدمن فقط.")
        return

    orders_data = load_orders()
    pending_orders = [o for o in orders_data if o["status"] == "pending"]

    if not pending_orders:
        await update.message.reply_text("ماكو طلبات pending حالياً.")
        return

    text = "⏳ الطلبات المعلقة:\n\n"
    for i, order in enumerate(pending_orders[-10:], start=1):
        text += (
            f"{i}. {order['name']} | {order['email']} | "
            f"{order['user_id']}\n"
        )

    await update.message.reply_text(text)


async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("هذا الأمر للأدمن فقط.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("الاستخدام:\n/approve USER_ID")
        return

    target_user_id = context.args[0]
    orders_data = load_orders()
    found_order = None

    for order in orders_data:
        if str(order["user_id"]) == str(target_user_id) and order["status"] == "pending":
            found_order = order
            break

    if not found_order:
        await update.message.reply_text("ما لكيت طلب pending لهذا المستخدم.")
        return

    pro_code, expires_date = create_pro_code_for_user(found_order["name"])

    found_order["status"] = "approved"
    found_order["pro_code"] = pro_code
    found_order["approved_at"] = datetime.now().isoformat()
    save_orders(orders_data)

    await context.bot.send_message(
        chat_id=target_user_id,
        text=(
            "✅ تم قبول طلبك\n\n"
            f"كود التفعيل مالك:\n{pro_code}\n\n"
            f"تاريخ الانتهاء: {expires_date}\n\n"
            "استخدمه داخل التطبيق لتفعيل النسخة المدفوعة."
        ),
    )

    await update.message.reply_text(
        f"تمت الموافقة على الطلب.\n"
        f"الكود: {pro_code}\n"
        f"ينتهي: {expires_date}"
    )


async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("هذا الأمر للأدمن فقط.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("الاستخدام:\n/reject USER_ID")
        return

    target_user_id = context.args[0]
    orders_data = load_orders()
    found = False

    for order in orders_data:
        if str(order["user_id"]) == str(target_user_id) and order["status"] == "pending":
            order["status"] = "rejected"
            found = True
            break

    save_orders(orders_data)

    if not found:
        await update.message.reply_text("ما لكيت طلب pending لهذا المستخدم.")
        return

    await context.bot.send_message(
        chat_id=target_user_id,
        text="❌ تم رفض الطلب. إذا صار خطأ، راسلنا من جديد."
    )

    await update.message.reply_text("تم رفض الطلب.")


async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("هذا الأمر للأدمن فقط.")
        return

    if len(context.args) < 3:
        await update.message.reply_text(
            "الاستخدام:\n/generate NAME DAYS MAX_USES\n\n"
            "مثال:\n/generate Saad 30 1"
        )
        return

    name = context.args[0]
    try:
        days_valid = int(context.args[1])
        max_uses = int(context.args[2])
    except ValueError:
        await update.message.reply_text("DAYS و MAX_USES لازم أرقام.")
        return

    pro_code, expires_date = create_pro_code_for_user(name, days_valid, max_uses)

    await update.message.reply_text(
        f"✅ تم إنشاء كود جديد\n\n"
        f"الاسم: {name}\n"
        f"الكود: {pro_code}\n"
        f"ينتهي: {expires_date}\n"
        f"عدد الاستخدامات: {max_uses}"
    )


async def codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("هذا الأمر للأدمن فقط.")
        return

    pro_codes = load_pro_codes()

    if not pro_codes:
        await update.message.reply_text("ماكو أكواد حالياً.")
        return

    text = "🔑 آخر الأكواد:\n\n"
    items = list(pro_codes.items())[-10:]

    for code, info in items:
        text += (
            f"{code} | {info['name']} | "
            f"exp: {info['expires']} | "
            f"used: {info['used']} | "
            f"max: {info['max_uses']}\n"
        )

    await update.message.reply_text(text)


async def deletecode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("هذا الأمر للأدمن فقط.")
        return

    if len(context.args) < 1:
        await update.message.reply_text("الاستخدام:\n/deletecode CODE")
        return

    code = context.args[0]
    pro_codes = load_pro_codes()

    if code not in pro_codes:
        await update.message.reply_text("ما لكيت هذا الكود.")
        return

    del pro_codes[code]
    save_pro_codes(pro_codes)

    await update.message.reply_text(f"🗑️ تم حذف الكود: {code}")


# =========================
# Main
# =========================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("orders", orders))
    app.add_handler(CommandHandler("pending", pending))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("reject", reject))
    app.add_handler(CommandHandler("generate", generate))
    app.add_handler(CommandHandler("codes", codes))
    app.add_handler(CommandHandler("deletecode", deletecode))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
