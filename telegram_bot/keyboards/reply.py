from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

def main_menu_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="🛍 Katalog"), KeyboardButton(text="🖼 Fasonlar Albomi")],
        [KeyboardButton(text="📦 Mening buyurtmalarim"), KeyboardButton(text="📞 Biz bilan aloqa")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def admin_menu_keyboard() -> ReplyKeyboardMarkup:
    # 9 modules based on the Web ERP sidebar + WebApp
    keyboard = [
        [KeyboardButton(text="🌐 ERP Tizimiga Kirish", web_app=WebAppInfo(url="https://tunika-erp.onrender.com"))],
        [KeyboardButton(text="🚀 Dashboard"), KeyboardButton(text="💰 Sotuv (POS)")],
        [KeyboardButton(text="🛒 Katalog"), KeyboardButton(text="🏢 Ombor")],
        [KeyboardButton(text="👥 Mijozlar"), KeyboardButton(text="💸 Xarajatlar")],
        [KeyboardButton(text="🖼 Albom"), KeyboardButton(text="📊 Hisobotlar")],
        [KeyboardButton(text="⚙️ Sozlamalar"), KeyboardButton(text="🔄 Saytdan sinxronlash")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
