from aiogram.fsm.state import StatesGroup, State

class OrderState(StatesGroup):
    waiting_for_meters = State()
    waiting_for_pieces = State()
    waiting_for_phone = State()
    confirm_order = State()

class POSState(StatesGroup):
    waiting_for_product_id = State()
    waiting_for_meters = State()
    waiting_for_pieces = State()
    waiting_for_customer_id = State()

class ExpenseState(StatesGroup):
    waiting_for_name = State()
    waiting_for_amount = State()

class CustomerState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()

class AlbumState(StatesGroup):
    waiting_for_title = State()
    waiting_for_photo = State()

class ProductState(StatesGroup):
    waiting_for_id = State()
    waiting_for_name = State()
    waiting_for_price = State()
    waiting_for_stock = State()

class EditState(StatesGroup):
    waiting_for_product_id = State()
    waiting_for_product_value = State()
    
    waiting_for_customer_id = State()
    waiting_for_customer_value = State()
    
    waiting_for_expense_id = State()
    waiting_for_expense_value = State()
    
    waiting_for_album_id = State()
    waiting_for_album_value = State()

