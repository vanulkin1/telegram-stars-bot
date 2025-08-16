
from aiogram import types, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import bold

from data.db import get_total_users, get_top_spender, get_total_stars_bought, ban_user, unban_user, create_connection
import aiohttp
import logging

API_KEY = '4y5i6AxM7hGu6ev7En4u'
API_BALANCE_URL = "https://bankstars.helper20sms.ru/api/balance"
ADMIN_ID = 7163004463
DATABASE_FILE = "starsbot.db"


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


async def admin_command(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        text = "Админ-панель:"
        keyboard = create_admin_keyboard()
        await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer("У вас нет доступа.")


async def view_db_callback(query: types.CallbackQuery):
    total_users = get_total_users(DATABASE_FILE)
    top_spender_id, max_spent = get_top_spender(DATABASE_FILE)
    total_stars_bought = get_total_stars_bought(DATABASE_FILE)

    conn = create_connection(DATABASE_FILE)
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

    await query.bot.send_message(query.message.chat.id, text, parse_mode="HTML")
    await query.answer()


async def ban_user_callback(query: types.CallbackQuery):
    await query.bot.send_message(query.message.chat.id, "Введите ID пользователя, которого хотите заблокировать:")
    await query.answer()
    Dispatcher.get_current().register_message_handler(process_ban_user, content_types=types.ContentType.TEXT, state="waiting_for_ban_id")


async def process_ban_user(message: types.Message, state=None):
    try:
        user_id = int(message.text)
        if ban_user(DATABASE_FILE, user_id):
            await message.reply(f"Пользователь с ID {user_id} успешно заблокирован.")
        else:
            await message.reply(f"Не удалось заблокировать пользователя с ID {user_id}.")
    except ValueError:
        await message.reply("Неверный ID пользователя. Введите число.")
    finally:
        if state:
            await state.finish()

async def unban_user_callback(query: types.CallbackQuery):
    await query.bot.send_message(query.message.chat.id, "Введите ID пользователя, которого хотите разблокировать:")
    await query.answer()
    Dispatcher.get_current().register_message_handler(process_unban_user, content_types=types.ContentType.TEXT, state="waiting_for_unban_id")

async def process_unban_user(message: types.Message, state=None):
    try:
        user_id = int(message.text)
        if unban_user(DATABASE_FILE, user_id):
            await message.reply(f"Пользователь с ID {user_id} успешно разблокирован.")
        else:
            await message.reply(f"Не удалось разблокировать пользователя с ID {user_id}.")
    except ValueError:
        await message.reply("Неверный ID пользователя. Введите число.")
    finally:
        if state:
            await state.finish()


async def broadcast_callback(query: types.CallbackQuery):
    await query.bot.send_message(query.message.chat.id, "Введите текст объявления для рассылки:")
    await query.answer()
    Dispatcher.get_current().register_message_handler(process_broadcast_message, content_types=types.ContentType.TEXT, state="waiting_for_broadcast_message")


async def process_broadcast_message(message: types.Message, state=None):
    from data.db import get_all_user_ids
    user_ids = get_all_user_ids(DATABASE_FILE)
    success_count = 0
    fail_count = 0
    for user_id in user_ids:
        try:
            await message.bot.send_message(user_id, message.text)
            success_count += 1
        except Exception as e:
            logging.error(f"Failed to send broadcast to user {user_id}: {e}")
            fail_count += 1

    await message.reply(f"Объявление отправлено {success_count} пользователям. Ошибок: {fail_count}")
    if state:
        await state.finish()


async def check_api_balance_callback(query: types.CallbackQuery):
    balance_data = await check_api_balance()
    if balance_data and balance_data["status"]:
        balance = balance_data["data"]["balance"]
        text = f"Баланс API: {balance}"
    else:
        text = "Не удалось получить баланс API."
    await query.bot.send_message(query.message.chat.id, text)
    await query.answer()


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

def register_admin_handlers(dp: Dispatcher):
    dp.register_message_handler(admin_command, commands=['admin'], is_admin=True)
    dp.register_callback_query_handler(view_db_callback, text="view_db", is_admin=True)
    dp.register_callback_query_handler(ban_user_callback, text="ban_user", is_admin=True)
    dp.register_callback_query_handler(unban_user_callback, text="unban_user", is_admin=True)
    dp.register_callback_query_handler(broadcast_callback, text="broadcast", is_admin=True)
    dp.register_callback_query_handler(check_api_balance_callback, text="check_api_balance", is_admin=True)

