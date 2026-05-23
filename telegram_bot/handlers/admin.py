from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_IDS
from keyboards.reply import admin_menu_keyboard
from database.queries import (
    get_all_products, admin_add_pos_sale, get_dashboard_stats, 
    add_expense, add_customer, get_all_customers, add_album_photo, add_product,
    update_product, update_customer, update_expense, update_album, get_all_albums
)
from states.fsm import POSState, ExpenseState, CustomerState, AlbumState, ProductState, EditState
from aiogram.fsm.context import FSMContext

router = Router()

def is_admin(event):
    return event.from_user.id in ADMIN_IDS

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message):
        return await message.answer("Sizda admin huquqlari yo'q.")
    await message.answer("Admin paneliga xush kelibsiz!", reply_markup=admin_menu_keyboard())

# ---------------- 1. DASHBOARD ----------------
@router.message(F.text == "🚀 Dashboard")
async def show_dashboard(message: Message):
    if not is_admin(message): return
    stats = await get_dashboard_stats()
    text = (
        f"🚀 **Dashboard (Bugungi)**\n\n"
        f"📈 Bugungi Savdo: {stats['sales']:,.0f} so'm\n"
        f"📉 Xarajatlar: {stats['expenses']:,.0f} so'm\n"
        f"💎 Sof Foyda: {stats['profit']:,.0f} so'm\n"
    )
    await message.answer(text, parse_mode="Markdown")

# ---------------- 2. KATALOG (Yangi mahsulot qo'shish) ----------------
@router.message(F.text == "🛒 Katalog")
async def show_katalog(message: Message, state: FSMContext):
    if not is_admin(message): return
    products = await get_all_products()
    text = "🛒 **Katalog (Mahsulotlar)**\n\n"
    for p in products:
        text += f"ID: {p.id} | {p.name} - {p.price} so'm\n"
    text += "\n*Yangi mahsulot qo'shish uchun avval uning ID sini kiriting (raqamda) yuboring (Yoki bekor qilish uchun /cancel):*"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="edit_product")]
    ])
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)
    await state.set_state(ProductState.waiting_for_id)

@router.message(ProductState.waiting_for_id)
async def process_product_id(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        return await message.answer("Bekor qilindi.")
    try:
        pid = int(message.text)
        await state.update_data(product_id=pid)
        await message.answer("Endi mahsulot nomini kiriting:")
        await state.set_state(ProductState.waiting_for_name)
    except ValueError:
        await message.answer("Iltimos, ID ni faqat raqamda kiriting.")

@router.message(ProductState.waiting_for_name)
async def process_product_name(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        return await message.answer("Bekor qilindi.")
    await state.update_data(name=message.text)
    await message.answer("Mahsulot narxini kiriting (raqamda):")
    await state.set_state(ProductState.waiting_for_price)

@router.message(ProductState.waiting_for_price)
async def process_product_price(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        return await message.answer("Bekor qilindi.")
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await message.answer("Mahsulot qoldig'ini (soni yoki metrini) kiriting (raqamda):")
        await state.set_state(ProductState.waiting_for_stock)
    except ValueError:
        await message.answer("Iltimos, narxni raqamda kiriting.")

@router.message(ProductState.waiting_for_stock)
async def process_product_stock(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        return await message.answer("Bekor qilindi.")
    try:
        stock = float(message.text)
        data = await state.get_data()
        try:
            await add_product(data['product_id'], data['name'], data['price'], stock)
            await message.answer("Mahsulot muvaffaqiyatli qo'shildi!")
            await state.clear()
        except Exception as e:
            await message.answer("Xatolik: Bu ID band bo'lishi mumkin yoki xato yuz berdi. Iltimos tekshirib qayta urinib ko'ring yoki /cancel bosing.")
    except ValueError:
        await message.answer("Iltimos, qoldiqni raqamda kiriting.")

# ---------------- 3. OMBOR ----------------
@router.message(F.text == "🏢 Ombor")
async def check_stock(message: Message):
    if not is_admin(message): return
    products = await get_all_products()
    text = "🏢 **Ombordagi qoldiqlar:**\n\n"
    for p in products:
        text += f"🔹 ID: {p.id} | {p.name} - Qoldiq: {p.stock_quantity}\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="edit_product")]
    ])
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

# ---------------- 4. SOTUV (POS) ----------------
@router.message(F.text == "💰 Sotuv (POS)")
async def new_pos_sale(message: Message, state: FSMContext):
    if not is_admin(message): return
    await message.answer("Sotilgan mahsulot ID sini kiriting:")
    await state.set_state(POSState.waiting_for_product_id)

@router.message(POSState.waiting_for_product_id)
async def process_pos_product(message: Message, state: FSMContext):
    try:
        pid = int(message.text)
        await state.update_data(product_id=pid)
        await message.answer("Sotilgan mahsulot uzunligini (metrini) kiriting:")
        await state.set_state(POSState.waiting_for_meters)
    except ValueError:
        await message.answer("ID faqat raqam bo'lishi kerak.")

@router.message(POSState.waiting_for_meters)
async def process_pos_meters(message: Message, state: FSMContext):
    try:
        meters = float(message.text)
        await state.update_data(meters=meters)
        await message.answer("Necha dona sotildi?")
        await state.set_state(POSState.waiting_for_pieces)
    except ValueError:
        await message.answer("Metrni raqamda kiriting.")

@router.message(POSState.waiting_for_pieces)
async def process_pos_pieces(message: Message, state: FSMContext):
    try:
        pieces = float(message.text)
        data = await state.get_data()
        meters = data['meters']
        total_quantity = meters * pieces
        
        def fmt(val):
            return int(val) if float(val).is_integer() else val
            
        success, msg, order_id = await admin_add_pos_sale(data['product_id'], total_quantity, do_print=False)
        
        if success and order_id:
            from database.queries import get_product_by_id
            product = await get_product_by_id(data['product_id'])
            total_price = product.price * total_quantity
            
            detailed_msg = (
                f"✅ **Sotuv tasdiqlandi!**\n\n"
                f"📦 Mahsulot: {product.name}\n"
                f"📏 O'lchami: {fmt(meters)} m  x  {fmt(pieces)} dona\n"
                f"📐 Umumiy uzunligi: **{fmt(total_quantity)} metr**\n"
                f"💰 Umumiy summa: **{total_price:,.0f} so'm**\n\n"
                f"_(Eslatma: Bazada 1 metr narxi {fmt(product.price):,.0f} so'm deb kiritilgan)_"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🖨 Chop etish", callback_data=f"print_{order_id}")]
            ])
            await message.answer(detailed_msg, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await message.answer(msg)
            
        await state.clear()
    except ValueError:
        await message.answer("Dona sonini raqamda kiriting.")

@router.callback_query(F.data.startswith("print_"))
async def process_print_receipt(callback: CallbackQuery):
    from database.queries import print_order_receipt
    order_id = int(callback.data.split("_")[1])
    success = await print_order_receipt(order_id)
    if success:
        await callback.answer("Chek printerga yuborildi!", show_alert=True)
    else:
        await callback.answer("Buyurtma topilmadi yoki xatolik yuz berdi.", show_alert=True)

# ---------------- 5. MIJOZLAR ----------------
@router.message(F.text == "👥 Mijozlar")
async def show_customers(message: Message, state: FSMContext):
    if not is_admin(message): return
    customers = await get_all_customers()
    text = "👥 **Mijozlar ro'yxati:**\n\n"
    for c in customers:
        text += f"ID: {c.id} | {c.name} | Xaridi: {c.total_spent}\n"
    text += "\n*Yangi mijoz qo'shish uchun ismini yozing (yoki /cancel):*"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="edit_customer")]
    ])
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)
    await state.set_state(CustomerState.waiting_for_name)

@router.message(CustomerState.waiting_for_name)
async def process_customer_name(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        return await message.answer("Bekor qilindi.")
    await state.update_data(name=message.text)
    await message.answer("Telefon raqamini kiriting:")
    await state.set_state(CustomerState.waiting_for_phone)

@router.message(CustomerState.waiting_for_phone)
async def process_customer_phone(message: Message, state: FSMContext):
    data = await state.get_data()
    await add_customer(data['name'], message.text)
    await message.answer("Mijoz saqlandi!")
    await state.clear()

# ---------------- 6. XARAJATLAR ----------------
@router.message(F.text == "💸 Xarajatlar")
async def show_expenses(message: Message, state: FSMContext):
    if not is_admin(message): return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="edit_expense")]
    ])
    await message.answer("Yangi xarajat qo'shish uchun nomini kiriting (Masalan: Yo'lkira):", reply_markup=keyboard)
    await state.set_state(ExpenseState.waiting_for_name)

@router.message(ExpenseState.waiting_for_name)
async def process_expense_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Xarajat summasini kiriting (raqamda):")
    await state.set_state(ExpenseState.waiting_for_amount)

@router.message(ExpenseState.waiting_for_amount)
async def process_expense_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
        data = await state.get_data()
        await add_expense(data['name'], amount)
        await message.answer("Xarajat saqlandi!")
        await state.clear()
    except ValueError:
        await message.answer("Summani raqamda kiriting.")

# ---------------- 7. ALBOM ----------------
@router.message(F.text == "🖼 Albom")
async def show_album(message: Message, state: FSMContext):
    if not is_admin(message): return
    albums = await get_all_albums()
    text = "🖼 **Albomdagi rasmlar:**\n\n"
    for a in albums:
        text += f"ID: {a.id} | {a.title}\n"
    text += "\n*Yangi rasm (fason) saqlash uchun rasm yuboring:*"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="edit_album")]
    ])
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)
    await state.set_state(AlbumState.waiting_for_photo)

@router.message(AlbumState.waiting_for_photo, F.photo)
async def process_album_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo=photo_id)
    await message.answer("Bu fason (rasm) nomini kiriting:")
    await state.set_state(AlbumState.waiting_for_title)

@router.message(AlbumState.waiting_for_title)
async def process_album_title(message: Message, state: FSMContext):
    data = await state.get_data()
    await add_album_photo(message.text, data['photo'])
    await message.answer("Rasm albomga saqlandi!")
    await state.clear()

# ---------------- 8 & 9. QOLGAN BO'LIMLAR ----------------
@router.message(F.text.in_(["📊 Hisobotlar", "⚙️ Sozlamalar"]))
async def show_other_menus(message: Message):
    if not is_admin(message): return
    await message.answer(f"{message.text} bo'limi hali ishlab chiqilmoqda...")

# ---------------- EDIT HANDLERS ----------------

@router.callback_query(F.data == "edit_product")
async def edit_product_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback): return
    await callback.message.answer("Tahrirlamoqchi bo'lgan mahsulot ID sini yuboring:")
    await state.set_state(EditState.waiting_for_product_id)
    await callback.answer()

@router.message(EditState.waiting_for_product_id)
async def edit_product_id(message: Message, state: FSMContext):
    if not is_admin(message): return
    try:
        pid = int(message.text)
        await state.update_data(edit_id=pid)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Nomi", callback_data="epf_name"),
             InlineKeyboardButton(text="Narxi", callback_data="epf_price"),
             InlineKeyboardButton(text="Qoldiq", callback_data="epf_stock")]
        ])
        await message.answer("Qaysi maydonni tahrirlaysiz?", reply_markup=keyboard)
    except ValueError:
        await message.answer("ID ni raqamda kiriting.")

@router.callback_query(F.data.startswith("epf_"))
async def edit_product_field(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback): return
    field = callback.data.split("_")[1]
    await state.update_data(edit_field=field)
    await callback.message.answer(f"Yangi qiymatni kiriting:")
    await state.set_state(EditState.waiting_for_product_value)
    await callback.answer()

@router.message(EditState.waiting_for_product_value)
async def edit_product_value(message: Message, state: FSMContext):
    if not is_admin(message): return
    data = await state.get_data()
    success = await update_product(data['edit_id'], data['edit_field'], message.text)
    if success:
        await message.answer("Muvaffaqiyatli tahrirlandi!")
    else:
        await message.answer("Mahsulot topilmadi yoki xatolik.")
    await state.clear()


@router.callback_query(F.data == "edit_customer")
async def edit_customer_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback): return
    await callback.message.answer("Tahrirlamoqchi bo'lgan mijoz ID sini yuboring:")
    await state.set_state(EditState.waiting_for_customer_id)
    await callback.answer()

@router.message(EditState.waiting_for_customer_id)
async def edit_customer_id(message: Message, state: FSMContext):
    if not is_admin(message): return
    try:
        cid = int(message.text)
        await state.update_data(edit_id=cid)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Ismi", callback_data="ecf_name"),
             InlineKeyboardButton(text="Telefon", callback_data="ecf_phone")]
        ])
        await message.answer("Qaysi maydonni tahrirlaysiz?", reply_markup=keyboard)
    except ValueError:
        await message.answer("ID ni raqamda kiriting.")

@router.callback_query(F.data.startswith("ecf_"))
async def edit_customer_field(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback): return
    field = callback.data.split("_")[1]
    await state.update_data(edit_field=field)
    await callback.message.answer(f"Yangi qiymatni kiriting:")
    await state.set_state(EditState.waiting_for_customer_value)
    await callback.answer()

@router.message(EditState.waiting_for_customer_value)
async def edit_customer_value(message: Message, state: FSMContext):
    if not is_admin(message): return
    data = await state.get_data()
    success = await update_customer(data['edit_id'], data['edit_field'], message.text)
    if success:
        await message.answer("Muvaffaqiyatli tahrirlandi!")
    else:
        await message.answer("Mijoz topilmadi yoki xatolik.")
    await state.clear()

@router.callback_query(F.data == "edit_expense")
async def edit_expense_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback): return
    await callback.message.answer("Tahrirlamoqchi bo'lgan xarajat ID sini yuboring:")
    await state.set_state(EditState.waiting_for_expense_id)
    await callback.answer()

@router.message(EditState.waiting_for_expense_id)
async def edit_expense_id(message: Message, state: FSMContext):
    if not is_admin(message): return
    try:
        eid = int(message.text)
        await state.update_data(edit_id=eid)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Nomi", callback_data="eef_name"),
             InlineKeyboardButton(text="Summasi", callback_data="eef_amount")]
        ])
        await message.answer("Qaysi maydonni tahrirlaysiz?", reply_markup=keyboard)
    except ValueError:
        await message.answer("ID ni raqamda kiriting.")

@router.callback_query(F.data.startswith("eef_"))
async def edit_expense_field(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback): return
    field = callback.data.split("_")[1]
    await state.update_data(edit_field=field)
    await callback.message.answer(f"Yangi qiymatni kiriting:")
    await state.set_state(EditState.waiting_for_expense_value)
    await callback.answer()

@router.message(EditState.waiting_for_expense_value)
async def edit_expense_value(message: Message, state: FSMContext):
    if not is_admin(message): return
    data = await state.get_data()
    success = await update_expense(data['edit_id'], data['edit_field'], message.text)
    if success:
        await message.answer("Muvaffaqiyatli tahrirlandi!")
    else:
        await message.answer("Xarajat topilmadi yoki xatolik.")
    await state.clear()

@router.callback_query(F.data == "edit_album")
async def edit_album_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback): return
    await callback.message.answer("Tahrirlamoqchi bo'lgan albom (rasm) ID sini yuboring:")
    await state.set_state(EditState.waiting_for_album_id)
    await callback.answer()

@router.message(EditState.waiting_for_album_id)
async def edit_album_id(message: Message, state: FSMContext):
    if not is_admin(message): return
    try:
        aid = int(message.text)
        await state.update_data(edit_id=aid)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Nomi", callback_data="eaf_title")]
        ])
        await message.answer("Qaysi maydonni tahrirlaysiz?", reply_markup=keyboard)
    except ValueError:
        await message.answer("ID ni raqamda kiriting.")

@router.callback_query(F.data.startswith("eaf_"))
async def edit_album_field(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback): return
    field = callback.data.split("_")[1]
    await state.update_data(edit_field=field)
    await callback.message.answer(f"Yangi qiymatni kiriting:")
    await state.set_state(EditState.waiting_for_album_value)
    await callback.answer()

@router.message(EditState.waiting_for_album_value)
async def edit_album_value(message: Message, state: FSMContext):
    if not is_admin(message): return
    data = await state.get_data()
    success = await update_album(data['edit_id'], data['edit_field'], message.text)
    if success:
        await message.answer("Muvaffaqiyatli tahrirlandi!")
    else:
        await message.answer("Albom topilmadi yoki xatolik.")
    await state.clear()
