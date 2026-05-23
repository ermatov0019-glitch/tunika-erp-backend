from datetime import datetime, date
import os
from sqlalchemy import select, update, func
from sqlalchemy.orm import selectinload
from database.engine import async_session
from database.models import Product, Order, OrderItem, Expense, Customer, Album

import webbrowser

def print_receipt(customer_name: str, product_name: str, quantity: float, price: float, total: float):
    try:
        # Txt file generation logic for backwards compatibility / fallback
        receipt_content = (
            "================================\n"
            "        BEST PROFNASTIL         \n"
            "================================\n"
            f"Sana: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Mijoz: {customer_name}\n"
            "--------------------------------\n"
            f"Mahsulot: {product_name}\n"
            f"Miqdor: {quantity}\n"
            f"Narxi: {price:,.0f} so'm\n"
            "--------------------------------\n"
            f"JAMI: {total:,.0f} so'm\n"
            "================================\n"
            "       Xaridingiz uchun         \n"
            "           rahmat!              \n"
            "================================\n\n\n"
        )
        with open("receipt.txt", "w", encoding="utf-8") as f:
            f.write(receipt_content)
        
        # HTML template filling
        if os.path.exists("receipt_template.html"):
            with open("receipt_template.html", "r", encoding="utf-8") as f:
                html = f.read()
            
            html = html.replace("__CUSTOMER_NAME__", str(customer_name))
            html = html.replace("__PRODUCT_NAME__", str(product_name))
            html = html.replace("__PRODUCT_QTY__", str(quantity))
            html = html.replace("__PRODUCT_PRICE_FMT__", f"{price:,.0f}")
            html = html.replace("__PRODUCT_PRICE__", str(price))
            html = html.replace("__TOTAL_PRICE_FMT__", f"{total:,.0f}")
            
            with open("current_receipt.html", "w", encoding="utf-8") as f:
                f.write(html)
            
            # Open HTML file in default browser
            import urllib.request
            abs_path = os.path.abspath("current_receipt.html")
            url = "file://" + urllib.request.pathname2url(abs_path)
            webbrowser.open(url)
        else:
            # Fallback to local txt print if template not found
            if os.name == 'nt':
                os.startfile("receipt.txt", "print")
                
    except Exception as e:
        print(f"Print error: {e}")


# ---------------- PRODUCTS & WAREHOUSE ----------------
async def get_all_products():
    async with async_session() as session:
        stmt = select(Product)
        result = await session.execute(stmt)
        return result.scalars().all()

async def get_product_by_id(product_id: int):
    async with async_session() as session:
        return await session.get(Product, product_id)

async def add_product(product_id: int, name: str, price: float, stock: float):
    async with async_session() as session:
        product = Product(id=product_id, name=name, price=price, stock_quantity=stock)
        session.add(product)
        await session.commit()
        return True

async def update_product(product_id: int, field: str, value):
    async with async_session() as session:
        product = await session.get(Product, product_id)
        if not product: return False
        
        if field == "name":
            product.name = value
        elif field == "price":
            product.price = float(value)
        elif field == "stock":
            product.stock_quantity = float(value)
            
        await session.commit()
        return True

# ---------------- ORDERS & POS ----------------
async def create_order(user_id: int, product_id: int, quantity: float, phone: str):
    async with async_session() as session:
        async with session.begin():
            product = await session.get(Product, product_id, with_for_update=True)
            if not product or product.stock_quantity < quantity:
                return False, "Omborda yetarli mahsulot yo'q."
                
            product.stock_quantity -= quantity
            total_price = product.price * quantity
            order = Order(user_id=user_id, user_phone=phone, total_price=total_price)
            session.add(order)
            await session.flush()
            
            order_item = OrderItem(order_id=order.id, product_id=product.id, quantity=quantity, price_per_unit=product.price)
            session.add(order_item)
            
            # Print receipt
            print_receipt(phone, product.name, quantity, product.price, total_price)
            
        return True, f"Buyurtma qabul qilindi. Summa: {total_price:,.0f} so'm"

async def admin_add_pos_sale(product_id: int, quantity: float, customer_id: int = None, do_print: bool = False):
    async with async_session() as session:
        async with session.begin():
            product = await session.get(Product, product_id, with_for_update=True)
            if not product:
                return False, "Xato: Mahsulot topilmadi.", None
            
            # Ombordagi qoldiqdan ayiramiz (manfiyga ham o'tishi mumkin)
            product.stock_quantity -= quantity
            total_price = product.price * quantity
            order = Order(customer_id=customer_id, user_id=0, total_price=total_price, status="completed")
            session.add(order)
            await session.flush()
            
            order_item = OrderItem(order_id=order.id, product_id=product.id, quantity=quantity, price_per_unit=product.price)
            session.add(order_item)

            if customer_id:
                customer = await session.get(Customer, customer_id)
                if customer:
                    customer.total_spent += total_price
                    customer_name = customer.name
                else:
                    customer_name = "Noma'lum"
            else:
                customer_name = "Umumiy Mijoz"
                
            if do_print:
                # Print receipt
                print_receipt(customer_name, product.name, quantity, product.price, total_price)
                    
        return True, f"Sotuv tasdiqlandi. Umumiy summa: {total_price:,.0f} so'm", order.id

async def print_order_receipt(order_id: int):
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if not order: return False
        
        customer_name = "Umumiy Mijoz"
        if order.customer_id:
            customer = await session.get(Customer, order.customer_id)
            if customer: customer_name = customer.name
            
        # For simplicity, assuming 1 item per order in POS
        stmt = select(OrderItem).where(OrderItem.order_id == order_id)
        result = await session.execute(stmt)
        item = result.scalars().first()
        if not item: return False
        
        product = await session.get(Product, item.product_id)
        product_name = product.name if product else "Noma'lum"
        
        print_receipt(customer_name, product_name, item.quantity, item.price_per_unit, order.total_price)
        return True

# ---------------- EXPENSES ----------------
async def add_expense(name: str, amount: float):
    async with async_session() as session:
        expense = Expense(name=name, amount=amount)
        session.add(expense)
        await session.commit()
        return True

async def update_expense(expense_id: int, field: str, value):
    async with async_session() as session:
        expense = await session.get(Expense, expense_id)
        if not expense: return False
        
        if field == "name":
            expense.name = value
        elif field == "amount":
            expense.amount = float(value)
            
        await session.commit()
        return True

async def get_today_expenses():
    today = date.today()
    async with async_session() as session:
        stmt = select(func.sum(Expense.amount)).where(func.date(Expense.date) == today)
        result = await session.execute(stmt)
        return result.scalar() or 0.0

# ---------------- CUSTOMERS ----------------
async def add_customer(name: str, phone: str):
    async with async_session() as session:
        customer = Customer(name=name, phone=phone)
        session.add(customer)
        await session.commit()
        return True

async def update_customer(customer_id: int, field: str, value):
    async with async_session() as session:
        customer = await session.get(Customer, customer_id)
        if not customer: return False
        
        if field == "name":
            customer.name = value
        elif field == "phone":
            customer.phone = value
            
        await session.commit()
        return True

async def get_all_customers():
    async with async_session() as session:
        stmt = select(Customer)
        result = await session.execute(stmt)
        return result.scalars().all()

# ---------------- ALBUMS ----------------
async def add_album_photo(title: str, photo_url: str):
    async with async_session() as session:
        album = Album(title=title, photo_url=photo_url)
        session.add(album)
        await session.commit()
        return True

async def get_all_albums():
    async with async_session() as session:
        stmt = select(Album)
        result = await session.execute(stmt)
        return result.scalars().all()

async def update_album(album_id: int, field: str, value):
    async with async_session() as session:
        album = await session.get(Album, album_id)
        if not album: return False
        
        if field == "title":
            album.title = value
            
        await session.commit()
        return True

# ---------------- DASHBOARD & REPORTS ----------------
async def get_dashboard_stats():
    today = date.today()
    async with async_session() as session:
        # Bugungi savdo
        stmt_sales = select(func.sum(Order.total_price)).where(func.date(Order.created_at) == today, Order.status == "completed")
        sales_result = await session.execute(stmt_sales)
        today_sales = sales_result.scalar() or 0.0
        
        # Bugungi xarajatlar
        stmt_exp = select(func.sum(Expense.amount)).where(func.date(Expense.date) == today)
        exp_result = await session.execute(stmt_exp)
        today_expenses = exp_result.scalar() or 0.0
        
        # Sof foyda (soddalashtirilgan)
        net_profit = today_sales - today_expenses
        
        return {
            "sales": today_sales,
            "expenses": today_expenses,
            "profit": net_profit
        }


# ---------------- USER ORDERS ----------------
async def create_order(user_id: int, product_id: int, quantity: float, user_phone: str):
    async with async_session() as session:
        async with session.begin():
            product = await session.get(Product, product_id, with_for_update=True)
            if not product:
                return False, "Xato: Mahsulot topilmadi.", None
            
            total_price = product.price * quantity
            order = Order(
                user_id=user_id, 
                user_phone=user_phone, 
                total_price=total_price, 
                status="pending"
            )
            session.add(order)
            await session.flush()
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=product_id,
                quantity=quantity,
                price_per_unit=product.price
            )
            session.add(order_item)
            
            return True, order.id, product


import aiohttp

# ---------------- SYNC API ----------------
async def sync_products_from_api():
    try:
        async with aiohttp.ClientSession() as http_session:
            async with http_session.get("https://tunika-erp.onrender.com/api/state") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    products = data.get("products", [])
                    
                    async with async_session() as db_session:
                        async with db_session.begin():
                            # Avval hammasini tozalash (yoki yangilash)
                            # Eng osoni: hammasini ochirib boshqatdan yozish
                            # yoki faqat qo'shish/yangilash
                            
                            # Fetch current ones
                            result = await db_session.execute(select(Product))
                            existing_products = {p.id: p for p in result.scalars().all()}
                            
                            for p_data in products:
                                pid = p_data.get("id")
                                name = p_data.get("name")
                                price = float(p_data.get("price", 0))
                                stock = float(p_data.get("stock", 0))
                                
                                if pid in existing_products:
                                    existing = existing_products[pid]
                                    existing.name = name
                                    existing.price = price
                                    existing.stock_quantity = stock
                                else:
                                    new_prod = Product(
                                        id=pid,
                                        name=name,
                                        description="Saytdan yuklandi",
                                        price=price,
                                        stock_quantity=stock,
                                        category_id=1,
                                        image_url=""
                                    )
                                    db_session.add(new_prod)
                            await db_session.flush()
                    return True, f"{len(products)} ta mahsulot muvaffaqiyatli sinxronlandi!"
                else:
                    return False, f"Saytdan ma'lumot olishda xatolik: {resp.status}"
    except Exception as e:
        return False, f"Xatolik yuz berdi: {e}"
