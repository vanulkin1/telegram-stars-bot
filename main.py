
import asyncio
import logging
import logging as logger

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import escape_md, bold, italic

from data.db import create_connection, create_tables, update_user_profile
from data.keyboards import create_main_menu_keyboard
from data.admin import register_admin_handlers
from aiocryptopay import AioCryptoPay, Networks
import aiohttp

API_KEY = '4y5i6AxM7hGu6ev7En4u'
BOT_TOKEN = "8110347269:AAFWjcoxcV-nQdS6yxBp7gnNylH01KHWULc"
ADMIN_ID = 7163004463
CRYPTO_PAY_TOKEN = "443925:AA1DMGV0OOCT3qJ93lRCRt14Z2ZXJ74LceL"

GET_PRICE_URL = "https://bankstars.helper20sms.ru/api/price"
MAKE_ORDER_URL = "https://bankstars.helper20sms.ru/api/order"
GET_ORDER_INFO_URL = "https://bankstars.helper20sms.ru/api/order"
API_BALANCE_URL = "https://bankstars.helper20sms.ru/api/balance"
payment_data = {}

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)
crypto = AioCryptoPay(token=CRYPTO_PAY_TOKEN, network=Networks.MAIN_NET)

DATABASE_FILE = "data/starsbot.db"
INVOICE_STORE = {}
USERNAME_STORE = {}

# Initialize the database
conn = create_connection(DATABASE_FILE)
create_tables(conn)
conn.close()

async def create_crypto_client():
    """Создание клиента CryptoBot в async контексте"""
    try:
        from aiocryptopay import AioCryptoPay, Networks
        crypto = AioCryptoPay(token=CRYPTO_PAY_TOKEN, network=Networks.MAIN_NET)
        return crypto
    except Exception as e:
        logger.error(f"Ошибка создания crypto клиента: {e}")
        return None

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

        INVOICE_STORE[user_id] = invoice.invoice_id

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
    update_user_profile(DATABASE_FILE, user_id, username)

    text = "Добро пожаловать в Stars Storage!\n\nВыберите действие:"
    await message.answer(text, reply_markup=create_main_menu_keyboard())


async def buy_stars_callback(query: types.CallbackQuery):
    from data.keyboards import create_username_choice_keyboard
    user_id = query.from_user.id
    username = query.from_user.username
    text = escape_md(f"⭐️ Покупка Звёзд\n\n🔎 Введите юзернейм пользователя, которому будем дарить звёзды:\n— Пример: @{username}")
    keyboard = create_username_choice_keyboard("STARS")
    await bot.edit_message_text(text, query.message.chat.id, query.message.message_id, reply_markup=keyboard,
                                parse_mode="Markdown")
    USERNAME_STORE[user_id] = {"item_type": "STARS"}
    await query.answer()


async def buy_premium_callback(query: types.CallbackQuery):
    from data.keyboards import create_username_choice_keyboard
    user_id = query.from_user.id
    username = query.from_user.username
    text = escape_md(f"👑 Покупка Премиум\n\n🔎 Введите юзернейм пользователя, которому будем дарить премиум:\n— Пример: @{username}")
    keyboard = create_username_choice_keyboard("PREMIUM")
    await bot.edit_message_text(text, query.message.chat.id, query.message.message_id, reply_markup=keyboard,
                                parse_mode="Markdown")
    USERNAME_STORE[user_id] = {"item_type": "PREMIUM"}
    await query.answer()


async def buy_for_self_callback(query: types.CallbackQuery):
    from data.keyboards import create_stars_amount_keyboard, create_premium_duration_keyboard
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
    from data.keyboards import create_main_menu_keyboard
    callback_data = query.data.split(":")
    item_type = callback_data[0].split("_")[1].upper()
    amount = int(callback_data[1])
    username = callback_data[2]

    price_data = await get_price(item_type, amount)
    if price_data and price_data["status"]:
        price = price_data["data"]["price"]

        if item_type == "STARS":
            text = escape_md(f"Вы уверены, что хотите преобрести {amount} звезд ⭐️ для @{username} за ${price}?")
        else:
            text = escape_md(f"Вы уверены, что хотите преобрести подписку Премиум на {amount} месяцев для @{username} за ${price}?")

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить",
                                    callback_data=f"process_payment:{item_type}:{amount}:{username}")],
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
    from data.keyboards import create_main_menu_keyboard
    callback_data = query.data.split(":")
    item_type = callback_data[1]
    amount = int(callback_data[2])
    username = callback_data[3]
    user_id = query.from_user.id

    invoice_url = await make_invoice(item_type, amount, user_id)

    if item_type == 'STARS':
        payment_data[user_id] = {
            "invoice_id": INVOICE_STORE[user_id] ,
            "stars": amount,
            "premium": None
        }
    else:
        payment_data[user_id] = {
            "invoice_id": INVOICE_STORE[user_id] ,
            "stars": None,
            "premium": amount
        }

    if invoice_url:
        text = f"💲 Счет для оплаты:\n\n{invoice_url}\n\nПосле оплаты счета товар будет отправлен на аккаунт "
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Я оплатил ✅",
                                    callback_data=f"check_payment:{item_type}:{amount}:{username}")]
        ])
        await bot.edit_message_text(text, query.message.chat.id, query.message.message_id, reply_markup=keyboard)
    else:
        text = "Ошибка создания счёта. Повторите позже."
        await bot.edit_message_text(text, query.message.chat.id, query.message.message_id,
                                reply_markup=create_main_menu_keyboard())
    await query.answer()


async def check_payment_callback(query: types.CallbackQuery):
    from data.keyboards import create_main_menu_keyboard
    from data.db import update_user_profile
    callback_data = query.data.split(":")
    item_type = callback_data[1]
    amount = int(callback_data[2])
    username = callback_data[3]
    user_id = query.from_user.id

    invoice_id = INVOICE_STORE.get(user_id)

    if invoice_id is None:
        text = "Счёт не найден. Пожалуйста, создайте новый счёт."
        await bot.edit_message_text(text, query.message.chat.id, query.message.message_id,
                                reply_markup=create_main_menu_keyboard())
        await query.answer()
        return

    crypto = await create_crypto_client()

    if not crypto:
        await bot.edit_message_text("❌ Ошибка платежной системы", query.message.chat.id, query.message.message_id)
        return

    invoice_id = payment_data[user_id]["invoice_id"]
    is_paid = await check_payment_status(invoice_id)  # Call the helper function

    if is_paid:
        try:
            order_result = await make_order(item_type.lower(), amount, username)

            if order_result and order_result["status"]:
                if item_type == "STARS":
                    update_user_profile(DATABASE_FILE, user_id, username, stars=amount)
                elif item_type == "PREMIUM":
                    update_user_profile(DATABASE_FILE, user_id, username, premium_months=amount)

                text = "✅ Заказ успешно выполнен, товар будет доставлен в течение 1 минуты\n\n❓Есть вопросы или столкнулись с проблемой? Обратитесь в поддержку — @new_vanulkin"

                if user_id in INVOICE_STORE:
                    del INVOICE_STORE[user_id]
            else:
                text = "Ошибка выполнения заказа. Повторите позже."
        except Exception as e:
            logging.exception(f"An unexpected error occurred: {e}")
            text = "Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже."
    else:
        text = "Оплата не подтверждена. Пожалуйста, убедитесь, что вы оплатили счёт, и попробуйте еще раз."

    await bot.edit_message_text(text, query.message.chat.id, query.message.message_id,
                            reply_markup=create_main_menu_keyboard())
    await query.answer()


async def profile_callback(query: types.CallbackQuery):
    from data.db import get_user_profile
    from data.keyboards import create_main_menu_keyboard
    user_id = query.from_user.id
    profile = get_user_profile(DATABASE_FILE, user_id)
    username = profile["username"] or "N/A"

    text = (
        bold("Ваш профиль") + "\n"
        f"Имя пользователя: @{username}\n"
        f"ID: <code>{user_id}</code>\n"
        f"⭐️ Куплено звёзд: {profile['stars_bought']} \n"
        f"👑 Премиум на (мес.): {profile['premium_months_bought']} "
    )
    await bot.edit_message_text(text, query.message.chat.id, query.message.message_id,
                            reply_markup=create_main_menu_keyboard())
    await query.answer()


async def faq_callback(query: types.CallbackQuery):
    from data.keyboards import create_faq_keyboard
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
    from data.keyboards import create_main_menu_keyboard
    text = "Добро пожаловать в Stars Storage!\n\nВыберите действие:"
    await bot.edit_message_text(text, query.message.chat.id, query.message.message_id,
                            reply_markup=create_main_menu_keyboard())
    await query.answer()


async def username_message_handler(message: types.Message):
    from data.keyboards import create_stars_amount_keyboard, create_premium_duration_keyboard
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
    from data.keyboards import create_main_menu_keyboard, create_faq_keyboard
    from data.db import get_user_profile

    dp.register_message_handler(start_command, commands=['start'])
    dp.register_callback_query_handler(buy_stars_callback, text="buy_stars")
    dp.register_callback_query_handler(buy_premium_callback, text="buy_premium")
    dp.register_callback_query_handler(buy_for_self_callback, lambda c: c.data.startswith("buy_for_self"))
    dp.register_callback_query_handler(confirm_purchase_callback,
                                    lambda c: c.data.startswith("confirm_stars") or c.data.startswith(
                                        "confirm_premium"))
    dp.register_callback_query_handler(process_payment_callback, lambda c: c.data.startswith("process_payment"))
    dp.register_callback_query_handler(check_payment_callback, lambda c: c.data.startswith("check_payment"))

    dp.register_callback_query_handler(profile_callback, text="profile")
    dp.register_callback_query_handler(faq_callback, text="faq")
    dp.register_callback_query_handler(back_to_main_menu_callback, text="back_to_main_menu")

    from data.admin import admin_command, view_db_callback, ban_user_callback, unban_user_callback, broadcast_callback, check_api_balance_callback
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
