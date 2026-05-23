import sys

with open('database/queries.py', 'a', encoding='utf-8') as f:
    f.write('''

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
''')
