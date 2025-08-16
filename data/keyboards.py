from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
