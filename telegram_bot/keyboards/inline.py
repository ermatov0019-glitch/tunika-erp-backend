from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="🛒 Buyurtma berish", callback_data=f"buy_{product_id}")],
        [InlineKeyboardButton(text="◀️ Ortga", callback_data="back_to_catalog")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
