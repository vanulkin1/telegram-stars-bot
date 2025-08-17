
import asyncio
import logging
import os
import json
import sqlite3
import logging as logger
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import escape_md, bold, italic
from aiocryptopay import AioCryptoPay, Networks

API_KEY = '4y5i6AxM7hGu6ev7En4u'
a = "8110347269:AAHP1AdO6fGGjRSsJTtP_fSXcwQJ4UWSjjs"
ADMIN_ID = 7163004463
CRYPTO_PAY_TOKEN = "443925:AAvkBli2db0LpRSaXFQiSr0z0nfvd2SIFmb"

GET_PRICE_URL = "https://bankstars.helper20sms.ru/api/price"
MAKE_ORDER_URL = "https://bankstars.helper20sms.ru/api/order"
GET_ORDER_INFO_URL = "https://bankstars.helper20sms.ru/api/order"
API_BALANCE_URL = "https://bankstars.helper20sms.ru/api/balance"
payment_data = {}


logging.basicConfig(level=logging.INFO)

bot = Bot(token=a, parse_mode="HTML")
dp = Dispatcher(bot)
crypto = AioCryptoPay(token=CRYPTO_PAY_TOKEN, network=Networks.MAIN_NET)

DATABASE_FILE = "starsbot.db"
INVOICE_STORE = {}
USERNAME_STORE = {}
PURCHASE_DATA = {}


def create_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    return conn


async def create_crypto_client():
    """Создание клиента CryptoBot в async контексте"""
    try:
        from aiocryptopay import AioCryptoPay, Networks
        crypto = AioCryptoPay(token=CRYPTO_PAY_TOKEN, network=Networks.MAIN_NET)
        return crypto
    except Exception as e:
        logger.error(f"Ошибка создания crypto клиента: {e}")
        return None


def create_tables(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            stars_bought INTEGER DEFAULT 0,
            premium_months_bought INTEGER DEFAULT 0,
            banned INTEGER DEFAULT 0
        )
    """)
    conn.commit()


conn = create_connection()
create_tables(conn)
conn.close()


def create_main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(text="⭐️ Звёзды", callback_data="buy_stars"),
        InlineKeyboardButton(text="👑 Премиум", callback_data="buy_premium"),
        InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
        InlineKeyboardButton(text="❓ F.A.Q.", callback_data="faq"),
    )
    return keyboard


def create_username_choice_keyboard(item_type: str, amount: int = 0) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="🎩 Для Себя", callback_data=f"buy_for_self:{item_type}:{amount}"))
    keyboard.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main_menu"))
    return keyboard


def create_stars_amount_keyboard(username: str) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton(text="50 ⭐️", callback_data=f"confirm_stars:50:{username}"),
        InlineKeyboardButton(text="75 ⭐️", callback_data=f"confirm_stars:75:{username}"),
        InlineKeyboardButton(text="100 ⭐️", callback_data=f"confirm_stars:100:{username}"),
        InlineKeyboardButton(text="250 ⭐️", callback_data=f"confirm_stars:250:{username}"),
        InlineKeyboardButton(text="500 ⭐️", callback_data=f"confirm_stars:500:{username}"),
        InlineKeyboardButton(text="1 000 ⭐️", callback_data=f"confirm_stars:1000:{username}"),
        InlineKeyboardButton(text="2 500 ⭐️", callback_data=f"confirm_stars:2500:{username}"),
        InlineKeyboardButton(text="5 000 ⭐️", callback_data=f"confirm_stars:10000:{username}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main_menu")
    )
    return keyboard


def create_premium_duration_keyboard(username: str) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=3)
    keyboard.add(
        InlineKeyboardButton(text="3 Месяца", callback_data=f"confirm_premium:3:{username}"),
        InlineKeyboardButton(text="6 Месяцев", callback_data=f"confirm_premium:6:{username}"),
        InlineKeyboardButton(text="12 Месяцев", callback_data=f"confirm_premium:12:{username}"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main_menu")
    )
    return keyboard


def create_faq_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(text="Техподдержка", url="https://t.me/new_vanulkin"),
        InlineKeyboardButton(text="Политика конфидециальности", url="https://telegra.ph/Politika-konfidencialnosti-08-16-16"),
        InlineKeyboardButton(text="Пользовательское соглашение", url="https://telegra.ph/Polzovatelskoe-soglashenie-08-16-8"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main_menu")
    )
    return keyboard


def create_admin_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(text="Просмотр БД", callback_data="view_db"),
        InlineKeyboardButton(text="Заблокировать", callback_data="ban_user"),
        InlineKeyboardButton(text="Разблокировать", callback_data="unban_user"),
        InlineKeyboardButton(text="Объявление", callback_data="broadcast"),
        InlineKeyboardButton(text="Баланс API", callback_data="check_api_balance"),
        InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main_menu")
    )
    return keyboard


def get_user_profile(user_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, stars_bought, premium_months_bought, banned FROM users WHERE user_id = ?",
                   (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        username, stars_bought, premium_months_bought, banned = result
        return {"username": username, "stars_bought": stars_bought,
                "premium_months_bought": premium_months_bought, "banned": bool(banned)}
    else:
        return {"username": None, "stars_bought": 0, "premium_months_bought": 0, "banned": False}


def update_user_profile(user_id, username, stars=0, premium_months=0):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (user_id, username, stars_bought, premium_months_bought) VALUES (?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET username=?, stars_bought=stars_bought + ?, premium_months_bought=premium_months_bought + ?",
            (user_id, username, stars, premium_months, username, stars, premium_months),
        )
        conn.commit()
    except Exception as e:
        logging.error(f"Database update error: {e}")
    finally:
        conn.close()


def ban_user(user_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def unban_user(user_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET banned = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def get_total_users():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_top_spender():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, stars_bought + premium_months_bought FROM users ORDER BY stars_bought + premium_months_bought DESC LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0], result[1]
    else:
        return None, 0


def get_total_stars_bought():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(stars_bought) FROM users")
    total = cursor.fetchone()[0]
    conn.close()
    return total if total else 0


def get_all_user_ids():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return ids


async def get_price(item_type: str, amount: int) -> dict:
    async with aiohttp.ClientSession() as session:
        url = f"{GET_PRICE_URL}/{item_type}/{amount}"
        headers = {"X-api-key": API_KEY}
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logging.error(f"Error fetching price: {e}")
            return None


async def make_order(item_type: str, amount: int, recipient: str) -> dict:
    async with aiohttp.ClientSession() as session:
        headers = {"X-api-key": API_KEY}
        data = {"type": item_type.upper(), "amount": amount, "recipient": recipient}  # Convert item_type to uppercase
        logging.debug(f"Sending data to make_order API: {data}")
        try:
            async with session.post(MAKE_ORDER_URL, headers=headers, json=data) as response:
                try:
                    response.raise_for_status()
                    return await response.json()
                except aiohttp.ClientResponseError as e:
                    text = await response.text()
                    logging.error(f"Error making order: {e.status}, message='{e.message}', url='{e.request_info.url}', response_text='{text}'")
                    return None
        except aiohttp.ClientError as e:
            logging.error(f"Error making order: {e}")
            return None


async def get_order_info(order_id: int) -> dict:
    async with aiohttp.ClientSession() as session:
        headers = {"X-api-key": API_KEY}
        url = f"{GET_ORDER_INFO_URL}/{order_id}"
        try:
            async with session.get(url, headers=headers) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logging.error(f"Error getting order info: {e}")
            return None


async def check_api_balance():
    async with aiohttp.ClientSession() as session:
        headers = {"X-api-key": API_KEY}
        try:
            async with session.get(API_BALANCE_URL, headers=headers) as response:
                response.raise_for_status()
                data = await response.json()
                return data
        except aiohttp.ClientError as e:
            logging.error(f"Error checking API balance: {e}")
            return None


async def make_invoice(item_type: str, amount: int, user_id: int):
    price_data = await get_price(item_type, amount)
    if not (price_data and price_data["status"]):
        return None

    price = float(price_data["data"]["price"])
    price_with_fee = price // 100 * 3 + 0.1 + price

    try:
        invoice = await crypto.create_invoice(asset='USDT', amount=price_with_fee)

        # Store invoice_id in PURCHASE_DATA instead of global INVOICE_STORE
        if user_id not in PURCHASE_DATA:
            PURCHASE_DATA[user_id] = {}
        PURCHASE_DATA[user_id]['invoice_id'] = invoice.invoice_id

        return invoice.bot_invoice_url
    except Exception as e:
        logging.error(f"Error creating invoice: {e}")
        return None


async def check_payment_status(invoice_id: int) -> bool:
    """Проверяет статус оплаты счета CryptoPay."""
    try:
        invoices = await crypto.get_invoices(invoice_ids=str(invoice_id))
        if invoices:  # Check if the list is not empty
            if len(invoices) > 0:
                invoice = invoices[0]  # Access the first (and likely only) invoice
                if invoice.status == "paid":
                    return True
                else:
                    logging.info(f"Invoice {invoice_id} status: {invoice.status}")
                    return False
            else:
                logging.warning(f"No invoices found for invoice_id: {invoice_id}")
                return False
        else:
            logging.warning(f"Could not retrieve invoices for invoice_id: {invoice_id}")
            return False


    except Exception as e:
        logging.error(f"Error checking invoice status: {e}", exc_info=True)
        return False


async def start_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    update_user_profile(user_id, username)

    text = "Добро пожаловать в Stars Storage!\n\nВыберите действие:"
    await message.answer(text, reply_markup=create_main_menu_keyboard())


async def buy_stars_callback(query: types.CallbackQuery):
    user_id = query.from_user.id
    username = query.from_user.username
    text = escape_md(f"⭐️ Покупка Звёзд\n\n🔎 Введите юзернейм пользователя, которому будем дарить звёзды:\n— Пример: @{username}")
    keyboard = create_username_choice_keyboard("STARS")
    await bot.edit_message_text(text, query.message.chat.id, query.message.message_id, reply_markup=keyboard,
                                parse_mode="Markdown")
    USERNAME_STORE[user_id] = {"item_type": "STARS"}
    await query.answer()


async def buy_premium_callback(query: types.CallbackQuery):
    user_id = query.from_user.id
    username = query.from_user.username
    text = escape_md(f"👑 Покупка Премиум\n\n🔎 Введите юзернейм пользователя, которому будем дарить премиум:\n— Пример: @{username}")
    keyboard = create_username_choice_keyboard("PREMIUM")
    await bot.edit_message_text(text, query.message.chat.id, query.message.message_id, reply_markup=keyboard,
                                parse_mode="Markdown")
    USERNAME_STORE[user_id] = {"item_type": "PREMIUM"}
    await query.answer()


async def buy_for_self_callback(query: types.CallbackQuery):
    callback_data = query.data.split(":")
    item_type = callback_data[1]
    amount = int(callback_data[2]) if len(callback_data) > 2 else 0

    user_id = query.from_user.id
    username = query.from_user.username

    if item_type == "STARS":
        text = escape_md(
            "⭐️ Покупка Звёзд\n\n👤 Получатель: @{}\n\n• Минимум: 50 ⭐️\n• Максимум (за раз): 5000 ⭐️\n\n🔎 Выберите количество звёзд:".format(
                username))
        keyboard = create_stars_amount_keyboard(username)
        await bot.edit_message_text(text, query.message.chat.id, query.message.message_id, reply_markup=keyboard,
                                parse_mode="MarkdownV2")

    elif item_type == "PREMIUM":
        text = escape_md("👑 Покупка Премиум\n\n👤 Получатель: @{}\n\n🔎 Выберите период:".format(username))
        keyboard = create_premium_duration_keyboard(username)
        await bot.edit_message_text(text, query.message.chat.id, query.message.message_id, reply_markup=keyboard,
                                parse_mode="MarkdownV2")

    await query.answer()


async def confirm_purchase_callback(query: types.CallbackQuery):
    callback_data = query.data.split(":")
    item_type = callback_data[0].split("_")[1].upper()
    amount = int(callback_data[1])
    username = callback_data[2]
    user_id = query.from_user.id

    # Store purchase details in PURCHASE_DATA
    if user_id not in PURCHASE_DATA:
        PURCHASE_DATA[user_id] = {}
    PURCHASE_DATA[user_id]['item_type'] = item_type
    PURCHASE_DATA[user_id]['amount'] = amount
    PURCHASE_DATA[user_id]['username'] = username


    price_data = await get_price(item_type, amount)
    if price_data and price_data["status"]:
        price = price_data["data"]["price"]

        if item_type == "STARS":
            text = escape_md(f"Вы уверены, что хотите преобрести {amount} звезд ⭐️ для @{username} за ${price}?")
        else:
            text = escape_md(f"Вы уверены, что хотите преобрести подписку Премиум на {amount} месяцев для @{username} за ${price}?")

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить",
                                    callback_data="process_payment")],
            [InlineKeyboardButton(text="🚫 Отменить", callback_data="back_to_main_menu")]
        ])
        await bot.edit_message_text(text, query.message.chat.id, query.message.message_id, reply_markup=keyboard,
                                parse_mode="MarkdownV2")

    else:
        text = "Ошибка получения цены. Повторите позже."
        await bot.edit_message_text(text, query.message.chat.id, query.message.message_id,
                                reply_markup=create_main_menu_keyboard())

    await query.answer()


async def process_payment_callback(query: types.CallbackQuery):
    user_id = query.from_user.id

    if user_id not in PURCHASE_DATA or 'item_type' not in PURCHASE_DATA[user_id] or 'amount' not in PURCHASE_DATA[user_id] or 'username' not in PURCHASE_DATA[user_id]:
        await bot.send_message(query.message.chat.id, "Данные о покупке не найдены. Пожалуйста, начните процесс покупки заново.", reply_markup=create_main_menu_keyboard())
        return

    item_type = PURCHASE_DATA[user_id]['item_type']
    amount = PURCHASE_DATA[user_id]['amount']
    username = PURCHASE_DATA[user_id]['username']

    invoice_url = await make_invoice(item_type, amount, user_id)

    if item_type == 'STARS':
        payment_data[user_id] = {
            "stars": amount,
            "premium": None
        }
    else:
        payment_data[user_id] = {
            "stars": None,
            "premium": amount
        }

    if invoice_url:
        text = f"💲 Счет для оплаты:\n\n{invoice_url}\n\nПосле оплаты счета товар будет отправлен на аккаунт "
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Я оплатил ✅",
                                    callback_data="check_payment")]
        ])
        await bot.edit_message_text(text, query.message.chat.id, query.message.message_id, reply_markup=keyboard)
    else:
        text = "Ошибка создания счёта. Повторите позже."
        await bot.edit_message_text(text, query.message.chat.id, query.message.message_id,
                                reply_markup=create_main_menu_keyboard())
    await query.answer()


async def check_payment_callback(query: types.CallbackQuery):
    user_id = query.from_user.id

    if user_id not in PURCHASE_DATA or 'item_type' not in PURCHASE_DATA[user_id] or 'amount' not in PURCHASE_DATA[user_id] or 'username' not in PURCHASE_DATA[user_id]:
        await bot.send_message(query.message.chat.id, "Данные о покупке не найдены. Пожалуйста, начните процесс покупки заново.", reply_markup=create_main_menu_keyboard())
        return

    item_type = PURCHASE_DATA[user_id]['item_type']
    amount = PURCHASE_DATA[user_id]['amount']
    username = PURCHASE_DATA[user_id]['username']

    if 'invoice_id' not in PURCHASE_DATA[user_id]:
        text = "Счёт не найден. Пожалуйста, создайте новый счёт."
        await bot.edit_message_text(text, query.message.chat.id, query.message.message_id,
                                reply_markup=create_main_menu_keyboard())
        await query.answer()
        return

    invoice_id = PURCHASE_DATA[user_id]['invoice_id']


    crypto = await create_crypto_client()

    if not crypto:
        bot.answer_callback_query(user_id, "❌ Произошла ошибка платежной системы. Попробуйте позже")
        return

    is_paid = await check_payment_status(invoice_id)  # Call the helper function

    if is_paid:
        try:
            order_result = await make_order(item_type.lower(), amount, username)

            if order_result and order_result["status"]:
                if item_type == "STARS":
                    update_user_profile(user_id, username, stars=amount)
                elif item_type == "PREMIUM":
                    update_user_profile(user_id, username, premium_months=amount)

                text = "✅ Заказ успешно выполнен, товар будет доставлен в течение 1 минуты\n\n❓Есть вопросы или столкнулись с проблемой? Обратитесь в поддержку — @new_vanulkin"
                # Clear PURCHASE_DATA after successful purchase
                del PURCHASE_DATA[user_id]

            else:
                bot.answer_callback_query(user_id, "❌ Произошла ошибка выполнения заказа. Попробуйте позже")
        except Exception as e:
            logging.exception(f"An unexpected error occurred: {e}")
            bot.answer_callback_query(user_id, "❌ Произошла неизвестная ошибка. Попробуйте позже")
    else:
        bot.answer_callback_query(user_id, "❌ Оплата не найдена")

    # await bot.edit_message_text(text, query.message.chat.id, query.message.message_id,
    #                         reply_markup=create_main_menu_keyboard())
    await query.answer()


async def profile_callback(query: types.CallbackQuery):
    user_id = query.from_user.id
    profile = get_user_profile(user_id)
    username = profile["username"] or "N/A"

    text = (
        bold("Ваш профиль") + "\n"
        f"Имя пользователя: {username}\n"
        f"ID: <code>{user_id}</code>\n"
        f"Куплено звёзд: {profile['stars_bought']} ✨\n"
        f"Премиум на (мес.): {profile['premium_months_bought']} 👑"
    )
    await bot.edit_message_text(text, query.message.chat.id, query.message.message_id,
                            reply_markup=create_main_menu_keyboard())
    await query.answer()


async def faq_callback(query: types.CallbackQuery):
    text = """
*Часто задаваемые вопросы и наши проекты*

— Как происходит выдача товара?
Звёзды вы получаете прямо на указанный при оформлении заказа аккаунт, и сразу же можете использовать их так, как пожелаете.

— Как вы даётся премиум?
Премиум выдаётся прямо на аккаунт, указанный при оформлении заказа (подарком), и вы сразу же получаете доступ ко всем премиум-функциям.

— Как быстро приходят звезды?
Заказы отправляются автоматически и, как правило, приходят в течение 15 секунд.

— Могу ли я покупать звезды только для себя?
Нет, вы можете отправлять подарки любым пользователям, у которых есть @username.

— Есть ли риск блокировки моего аккаунта или рефаунда звезд?
Нет, риск отсутствует, так как мы используем официальную платформу Telegram для покупки звёзд. Блокировка или потеря звёзд невозможны.

• [Правила сервиса](https://telegra.ph/Pravila-i-usloviya-ispolzovaniya-servisa-Stars-Storage-08-16).
• [Техническая поддержка](http://t.me/new_vanulkin).
    """
    keyboard = create_faq_keyboard()
    await bot.edit_message_text(text, query.message.chat.id, query.message.message_id, reply_markup=keyboard, parse_mode="Markdown")
    await query.answer()


async def back_to_main_menu_callback(query: types.CallbackQuery):
    text = "Добро пожаловать в Stars Storage!\n\nВыберите действие:"
    await bot.edit_message_text(text, query.message.chat.id, query.message.message_id,
                            reply_markup=create_main_menu_keyboard())
    await query.answer()


async def admin_command(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        text = "Админ-панель:"
        keyboard = create_admin_keyboard()
        await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer("У вас нет доступа.")


async def view_db_callback(query: types.CallbackQuery):
    total_users = get_total_users()
    top_spender_id, max_spent = get_top_spender()
    total_stars_bought = get_total_stars_bought()

    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    data = cursor.fetchall()
    conn.close()

    table_string = "user_id | username | stars_bought | premium_months_bought | banned\n"
    table_string += "-------|----------|-------------|----------------------|--------\n"
    for row in data:
        table_string += f"{row[0]:7} | {row[1]:8} | {row[2]:11} | {row[3]:20} | {row[4]:6}\n"

    text = (
        bold("Статистика") + "\n\n"
        f"Всего пользователей: {total_users}\n"
        f"Самый щедрый: ID {top_spender_id} (всего: {max_spent})\n"
        f"Всего куплено звёзд: {total_stars_bought} ✨\n\n"
        f"<pre>{table_string}</pre>"
    )

    await bot.send_message(query.message.chat.id, text, parse_mode="HTML")
    await query.answer()


async def ban_user_callback(query: types.CallbackQuery):
    pass


async def unban_user_callback(query: types.CallbackQuery):
    pass


async def broadcast_callback(query: types.CallbackQuery):
    pass


async def check_api_balance_callback(query: types.CallbackQuery):
    balance_data = await check_api_balance()
    if balance_data and balance_data["status"]:
        balance = balance_data["data"]["balance"]
        text = f"Баланс API: {balance}"
    else:
        text = "Не удалось получить баланс API."
    await bot.send_message(query.message.chat.id, text)
    await query.answer()


async def username_message_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.text.replace('@', '')

    if user_id in USERNAME_STORE:
        item_type = USERNAME_STORE[user_id]["item_type"]

        del USERNAME_STORE[user_id]

        if item_type == "STARS":
            text = escape_md(
                "⭐️ Покупка Звёзд\n\n👤 Получатель: @{}\n\n• Минимум: 50 ⭐️\n• Максимум (за раз): 5000 ⭐️\n\n🔎 Выберите количество звёзд:".format(
                    username))
            keyboard = create_stars_amount_keyboard(username)
            try:
                await bot.delete_message(message.chat.id, message.message_id)
                if message.reply_to_message:
                    await bot.delete_message(message.chat.id, message.reply_to_message.message_id)
            except Exception as e:
                logging.exception("Error deleting messages")
            await bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode="MarkdownV2")

        elif item_type == "PREMIUM":
            text = escape_md("👑 Покупка Премиум\n\n👤 Получатель: @{}\n\n🔎 Выберите период:".format(username))
            keyboard = create_premium_duration_keyboard(username)
            try:
                await bot.delete_message(message.chat.id, message.message_id)
                if message.reply_to_message:
                    await bot.delete_message(message.chat.id, message.reply_to_message.message_id)
            except Exception as e:
                logging.exception("Error deleting messages")
            await bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode="MarkdownV2")
    else:
        await bot.send_message(message.chat.id, "Не удалось определить, что вы хотите купить.")


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(start_command, commands=['start'])
    dp.register_callback_query_handler(buy_stars_callback, text="buy_stars")
    dp.register_callback_query_handler(buy_premium_callback, text="buy_premium")
    dp.register_callback_query_handler(buy_for_self_callback, lambda c: c.data.startswith("buy_for_self"))
    dp.register_callback_query_handler(confirm_purchase_callback,
                                    lambda c: c.data.startswith("confirm_stars") or c.data.startswith(
                                        "confirm_premium"))
    dp.register_callback_query_handler(process_payment_callback, text="process_payment")
    dp.register_callback_query_handler(check_payment_callback, text="check_payment")

    dp.register_callback_query_handler(profile_callback, text="profile")
    dp.register_callback_query_handler(faq_callback, text="faq")
    dp.register_callback_query_handler(back_to_main_menu_callback, text="back_to_main_menu")

    dp.register_message_handler(admin_command, commands=['admin'])
    dp.register_callback_query_handler(view_db_callback, text="view_db")
    dp.register_callback_query_handler(ban_user_callback, text="ban_user")
    dp.register_callback_query_handler(unban_user_callback, text="unban_user")
    dp.register_callback_query_handler(broadcast_callback, text="broadcast")
    dp.register_callback_query_handler(check_api_balance_callback, text="check_api_balance")
    dp.register_message_handler(username_message_handler, content_types=types.ContentType.TEXT)


async def main():
    register_handlers(dp)
    try:
        await dp.start_polling()
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
