from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from keyboards.reply import main_menu_keyboard
from keyboards.inline import get_product_keyboard
from database.queries import get_all_products
from states.fsm import OrderState
from aiogram.fsm.context import FSMContext

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        f"Salom, {message.from_user.first_name}! Tunika ERP botiga xush kelibsiz.\nQuyidagi menyudan kerakli bo'limni tanlang:",
        reply_markup=main_menu_keyboard()
    )

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@router.message(F.text == "🛍 Katalog")
async def show_catalog(message: Message):
    products = await get_all_products()
    if not products:
        await message.answer("Hozircha katalogda mahsulotlar yo'q.")
        return
        
    await message.answer("📦 **Bizdagi mahsulotlar katalogi:**\nMarhamat, o'zingizga kerakli mahsulotni tanlang:", parse_mode="Markdown")
    
    for product in products:
        text = f"🔹 **{product.name}**\n💰 Narxi: {product.price:,.0f} so'm"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Sotib olish", callback_data=f"buy_{product.id}")]
        ])
        await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@router.message(F.text == "📞 Biz bilan aloqa")
async def contact_us(message: Message):
    text = (
        "📞 **Biz bilan aloqa**\n\n"
        "Barcha savol va murojaatlar uchun quyidagi manzillarga murojaat qilishingiz mumkin:\n\n"
        "💬 **Telegram orqali:**\n"
        "1. [Administrator 1](https://t.me/Bekh_005) (@Bekh_005)\n"
        "2. [Administrator 2](https://t.me/ermatov004) (@ermatov004)\n\n"
        "📱 **Telefon raqamlar:**\n"
        "📞 +998934438887\n"
        "📞 +998940270019"
    )
    await message.answer(text, disable_web_page_preview=True, parse_mode="Markdown")

# Buyurtma berish logikasi (FSM bilan)
@router.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: CallbackQuery, state: FSMContext):
    product_id = int(callback.data.split("_")[1])
    await state.update_data(product_id=product_id)
    await callback.message.answer("Sizga bitta dona mahsulotning uzunligi qancha kerak? (metrda kiriting, masalan: 4.5)")
    await state.set_state(OrderState.waiting_for_meters)
    await callback.answer()

@router.message(OrderState.waiting_for_meters)
async def process_meters(message: Message, state: FSMContext):
    try:
        meters = float(message.text)
    except ValueError:
        await message.answer("Iltimos, uzunlikni raqamda kiriting (masalan: 4.5).")
        return
        
    await state.update_data(meters=meters)
    await message.answer("Shu uzunlikdan necha dona kerak bo'ladi? (raqam kiriting, masalan: 10)")
    await state.set_state(OrderState.waiting_for_pieces)

@router.message(OrderState.waiting_for_pieces)
async def process_pieces(message: Message, state: FSMContext):
    try:
        pieces = float(message.text)
    except ValueError:
        await message.answer("Iltimos, dona sonini raqamda kiriting.")
        return
        
    await state.update_data(pieces=pieces)
    await message.answer("Siz bilan bog'lanishimiz uchun telefon raqamingizni kiriting:\n(Masalan: +998901234567)")
    await state.set_state(OrderState.waiting_for_phone)

@router.message(OrderState.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text
    data = await state.get_data()
    
    meters = data['meters']
    pieces = data['pieces']
    total_quantity = meters * pieces
    
    from database.queries import create_order
    from config import ADMIN_IDS
    
    success, order_id, product = await create_order(message.from_user.id, data['product_id'], total_quantity, phone)
    
    if success:
        total_price = product.price * total_quantity
        def fmt(val):
            return int(val) if float(val).is_integer() else val
            
        admin_text = (
            f"🚨 **Yangi Buyurtma tushdi!**\n\n"
            f"👤 Mijoz: {message.from_user.full_name}\n"
            f"📞 Tel: {phone}\n"
            f"📦 Mahsulot: {product.name}\n"
            f"📏 O'lchami: {fmt(meters)} m x {fmt(pieces)} dona\n"
            f"📐 Umumiy: {fmt(total_quantity)} metr\n"
            f"💰 Summa: {total_price:,.0f} so'm\n\n"
            f"_(Buyurtma ID: {order_id})_"
        )
        
        for admin_id in ADMIN_IDS:
            try:
                await message.bot.send_message(chat_id=admin_id, text=admin_text, parse_mode="Markdown")
            except Exception:
                pass
                
        await message.answer(
            f"✅ **Buyurtmangiz muvaffaqiyatli qabul qilindi!**\n\n"
            f"📦 Mahsulot: {product.name}\n"
            f"📐 Jami uzunlik: {fmt(total_quantity)} metr\n"
            f"💰 Jami summa: {total_price:,.0f} so'm\n\n"
            f"Sizning raqamingiz: {phone}\n"
            f"Tez orada operatorlarimiz siz bilan bog'lanadi.",
            parse_mode="Markdown"
        )
    else:
        await message.answer("Xatolik yuz berdi. Iltimos qayta urinib ko'ring.")
        
    await state.clear()
