from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import sqlite3
import json
import os
import urllib.request

app = Flask(__name__)
CORS(app)

DB_PATH = os.environ.get('DB_PATH', 'db.sqlite')
DATABASE_URL = os.environ.get('DATABASE_URL')
USING_POSTGRES = DATABASE_URL is not None

def get_db():
    if USING_POSTGRES:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def get_cursor(conn):
    return conn.cursor()

def execute_query(cursor, query, params=()):
    if USING_POSTGRES:
        query = query.replace('?', '%s')
    cursor.execute(query, params)
    return cursor

def execute_many(cursor, query, params_list):
    if USING_POSTGRES:
        query = query.replace('?', '%s')
    cursor.executemany(query, params_list)
    return cursor

def row_to_dict(cursor, row):
    if row is None:
        return None
    if USING_POSTGRES:
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    else:
        return dict(row)

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    if USING_POSTGRES:
        # Products table
        execute_query(cursor, '''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock REAL NOT NULL,
            thickness TEXT,
            icon TEXT,
            image TEXT
        )''')
        
        # Inventory table
        execute_query(cursor, '''
        CREATE TABLE IF NOT EXISTS inventory (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            qty REAL NOT NULL,
            type TEXT NOT NULL,
            date TEXT NOT NULL
        )''')
        
        # Customers table
        execute_query(cursor, '''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            debt REAL DEFAULT 0
        )''')
        
        # Expenses table
        execute_query(cursor, '''
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            note TEXT
        )''')
        
        # Album Styles table
        execute_query(cursor, '''
        CREATE TABLE IF NOT EXISTS album_styles (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            image TEXT
        )''')
        
        # Sales table
        execute_query(cursor, '''
        CREATE TABLE IF NOT EXISTS sales (
            id BIGINT PRIMARY KEY,
            total REAL NOT NULL,
            date TEXT NOT NULL,
            customerId INTEGER,
            customerName TEXT,
            paymentMethod TEXT,
            items TEXT,
            archived INTEGER DEFAULT 0
        )''')
        
        # Settings table
        execute_query(cursor, '''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
    else:
        # SQLite table creation
        execute_query(cursor, '''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            stock REAL NOT NULL,
            thickness TEXT,
            icon TEXT,
            image TEXT
        )''')
        
        execute_query(cursor, '''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            qty REAL NOT NULL,
            type TEXT NOT NULL,
            date TEXT NOT NULL
        )''')
        
        execute_query(cursor, '''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            debt REAL DEFAULT 0
        )''')
        
        execute_query(cursor, '''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            note TEXT
        )''')
        
        execute_query(cursor, '''
        CREATE TABLE IF NOT EXISTS album_styles (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            image TEXT
        )''')
        
        execute_query(cursor, '''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY,
            total REAL NOT NULL,
            date TEXT NOT NULL,
            customerId INTEGER,
            customerName TEXT,
            paymentMethod TEXT,
            items TEXT,
            archived INTEGER DEFAULT 0
        )''')
        
        execute_query(cursor, '''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
    
    # Insert initial data if database is empty
    execute_query(cursor, 'SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0:
        initial_products = [
            (1, 'Tunikafon (Kafel)', 55000, 120, '0.45', '🏠', ''),
            (2, 'Tunikafon (Monterrey)', 62000, 85, '0.50', '🏠', ''),
            (3, 'Tunikafon (Klassik)', 48000, 200, '0.40', '🏠', ''),
            (4, 'Profnastil N10', 38000, 300, '0.35', '📋', ''),
            (5, 'Profnastil N20', 45000, 150, '0.45', '📋', ''),
            (6, 'Profnastil N35 (Tom)', 58000, 90, '0.50', '📋', ''),
            (7, 'Tunika (Yassi list)', 32000, 500, '0.30', '📄', '')
        ]
        execute_many(cursor, 'INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)', initial_products)
        
        initial_inventory = [
            ('Rulon List (Oq)', 1200, 'raw', '12.05.2026'),
            ('Rulon List (Shokolad)', 850, 'raw', '12.05.2026')
        ]
        execute_many(cursor, 'INSERT INTO inventory (name, qty, type, date) VALUES (?, ?, ?, ?)', initial_inventory)
        
        execute_query(cursor, 'INSERT INTO customers VALUES (?, ?, ?, ?, ?)', (1, 'Umumiy Mijoz', '', '', 0))
        
        initial_styles = [
            (1, 'Kafel - Shokolad', ''),
            (2, 'Monterrey - Qizil', '')
        ]
        execute_many(cursor, 'INSERT INTO album_styles VALUES (?, ?, ?)', initial_styles)
        
        execute_query(cursor, 'INSERT INTO settings VALUES (?, ?)', ('shopName', 'ERMATOV ERP'))
        execute_query(cursor, 'INSERT INTO settings VALUES (?, ?)', ('currency', "so'm"))
        
    conn.commit()
    conn.close()

# Serves frontend
@app.route('/')
def index():
    return send_file('index.html')

@app.route('/manifest.json')
def manifest():
    return send_file('manifest.json')

@app.route('/sw.js')
def sw():
    return send_file('sw.js')

@app.route('/libs/<path:filename>')
def serve_libs(filename):
    return send_from_directory('libs', filename)

# API: Get entire state
@app.route('/api/state', methods=['GET'])
def get_state():
    conn = get_db()
    cursor = conn.cursor()
    
    execute_query(cursor, 'SELECT * FROM products')
    products = [row_to_dict(cursor, row) for row in cursor.fetchall()]
    
    execute_query(cursor, 'SELECT * FROM inventory')
    inventory = [row_to_dict(cursor, row) for row in cursor.fetchall()]
    
    execute_query(cursor, 'SELECT * FROM customers')
    customers = [row_to_dict(cursor, row) for row in cursor.fetchall()]
    
    execute_query(cursor, 'SELECT * FROM expenses')
    expenses = [row_to_dict(cursor, row) for row in cursor.fetchall()]
    
    execute_query(cursor, 'SELECT * FROM album_styles')
    album_styles = [row_to_dict(cursor, row) for row in cursor.fetchall()]
    
    execute_query(cursor, 'SELECT * FROM sales')
    sales_rows = cursor.fetchall()
    
    sales = []
    for row in sales_rows:
        d = row_to_dict(cursor, row)
        d['items'] = json.loads(d['items'])
        sales.append(d)
        
    execute_query(cursor, 'SELECT * FROM settings')
    settings_rows = cursor.fetchall()
    settings = {}
    for r in settings_rows:
        d = row_to_dict(cursor, r)
        settings[d['key']] = d['value']
    
    conn.close()
    
    return jsonify({
        'products': products,
        'inventory': inventory,
        'customers': customers,
        'expenses': expenses,
        'albumStyles': album_styles,
        'sales': sales,
        'settings': settings
    })

# API: Sync Full Backup (Import Backup)
@app.route('/api/state/import', methods=['POST'])
def import_state():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Clear existing data
        execute_query(cursor, 'DELETE FROM products')
        execute_query(cursor, 'DELETE FROM inventory')
        execute_query(cursor, 'DELETE FROM customers')
        execute_query(cursor, 'DELETE FROM expenses')
        execute_query(cursor, 'DELETE FROM album_styles')
        execute_query(cursor, 'DELETE FROM sales')
        execute_query(cursor, 'DELETE FROM settings')
        
        for p in data.get('products', []):
            execute_query(cursor, 'INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)', 
                           (p['id'], p['name'], p['price'], p['stock'], p['thickness'], p['icon'], p.get('image', '')))
            
        for i in data.get('inventory', []):
            execute_query(cursor, 'INSERT INTO inventory (name, qty, type, date) VALUES (?, ?, ?, ?)', 
                           (i['name'], i['qty'], i['type'], i['date']))
            
        for c in data.get('customers', []):
            execute_query(cursor, 'INSERT INTO customers VALUES (?, ?, ?, ?, ?)', 
                           (c['id'], c['name'], c.get('phone', ''), c.get('address', ''), c.get('debt', 0)))
            
        for e in data.get('expenses', []):
            execute_query(cursor, 'INSERT INTO expenses (date, amount, category, note) VALUES (?, ?, ?, ?)', 
                           (e['date'], e['amount'], e['category'], e.get('note', '')))
            
        for s in data.get('albumStyles', []):
            execute_query(cursor, 'INSERT INTO album_styles VALUES (?, ?, ?)', 
                           (s['id'], s['name'], s.get('image', '')))
            
        for s in data.get('sales', []):
            execute_query(cursor, 'INSERT INTO sales (id, total, date, customerId, customerName, paymentMethod, items, archived) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', 
                           (s['id'], s['total'], s['date'], s['customerId'], s['customerName'], s['paymentMethod'], json.dumps(s['items']), s.get('archived', 0)))
            
        settings = data.get('settings', {})
        for k, v in settings.items():
            execute_query(cursor, 'INSERT INTO settings VALUES (?, ?)', (k, str(v)))
            
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 400
    finally:
        conn.close()

# API: Products CRUD
@app.route('/api/products', methods=['POST'])
def add_product():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    execute_query(cursor, 'INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)',
                   (data['id'], data['name'], data['price'], data['stock'], data['thickness'], data['icon'], data.get('image', '')))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/products/<int:pid>', methods=['PUT', 'DELETE'])
def handle_product(pid):
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'PUT':
        data = request.json
        execute_query(cursor, 'UPDATE products SET name=?, price=?, stock=?, thickness=?, icon=?, image=? WHERE id=?',
                       (data['name'], data['price'], data['stock'], data['thickness'], data['icon'], data.get('image', ''), pid))
    elif request.method == 'DELETE':
        execute_query(cursor, 'DELETE FROM products WHERE id=?', (pid,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

# API: Inventory CRUD
@app.route('/api/inventory', methods=['POST'])
def add_inventory():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    execute_query(cursor, 'INSERT INTO inventory (name, qty, type, date) VALUES (?, ?, ?, ?)',
                   (data['name'], data['qty'], data['type'], data['date']))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/inventory/<int:iid>', methods=['PUT', 'DELETE'])
def handle_inventory(iid):
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'PUT':
        data = request.json
        execute_query(cursor, 'UPDATE inventory SET qty=? WHERE id=?', (data['qty'], iid))
    elif request.method == 'DELETE':
        # In SQLite AUTOINCREMENT tables have ids, but in initial html it was an index.
        # We will handle it by Database ID
        execute_query(cursor, 'DELETE FROM inventory WHERE id=?', (iid,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

# API: Customers CRUD
@app.route('/api/customers', methods=['POST'])
def add_customer():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    execute_query(cursor, 'INSERT INTO customers VALUES (?, ?, ?, ?, ?)',
                   (data['id'], data['name'], data.get('phone', ''), data.get('address', ''), data.get('debt', 0)))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/customers/<int:cid>', methods=['PUT', 'DELETE'])
def handle_customer(cid):
    conn = get_db()
    cursor = conn.cursor()
    if request.method == 'PUT':
        data = request.json
        execute_query(cursor, 'UPDATE customers SET name=?, phone=?, address=?, debt=? WHERE id=?',
                       (data['name'], data.get('phone', ''), data.get('address', ''), data.get('debt', 0), cid))
    elif request.method == 'DELETE':
        execute_query(cursor, 'DELETE FROM customers WHERE id=?', (cid,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

# API: Expenses CRUD
@app.route('/api/expenses', methods=['POST'])
def add_expense():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    execute_query(cursor, 'INSERT INTO expenses (date, amount, category, note) VALUES (?, ?, ?, ?)',
                   (data['date'], data['amount'], data['category'], data.get('note', '')))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/expenses/<int:eid>', methods=['DELETE'])
def delete_expense(eid):
    conn = get_db()
    cursor = conn.cursor()
    execute_query(cursor, 'DELETE FROM expenses WHERE id=?', (eid,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

# API: Album Styles CRUD
@app.route('/api/album_styles', methods=['POST'])
def add_style():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    if USING_POSTGRES:
        execute_query(cursor, 'INSERT INTO album_styles (id, name, image) VALUES (?, ?, ?) ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, image = EXCLUDED.image',
                      (data['id'], data['name'], data.get('image', '')))
    else:
        execute_query(cursor, 'INSERT OR REPLACE INTO album_styles VALUES (?, ?, ?)',
                      (data['id'], data['name'], data.get('image', '')))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/album_styles/<int:sid>', methods=['DELETE'])
def delete_style(sid):
    conn = get_db()
    cursor = conn.cursor()
    execute_query(cursor, 'DELETE FROM album_styles WHERE id=?', (sid,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

# API: Sales (Checkout)
@app.route('/api/sales', methods=['POST'])
def add_sale():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Save sale
        execute_query(cursor, 'INSERT INTO sales (id, total, date, customerId, customerName, paymentMethod, items, archived) VALUES (?, ?, ?, ?, ?, ?, ?, 0)',
                       (data['id'], data['total'], data['date'], data['customerId'], data['customerName'], data['paymentMethod'], json.dumps(data['items'])))
        
        # Update customer debt if paymentMethod is 'Nasiya'
        if data['paymentMethod'] == 'Nasiya':
            execute_query(cursor, 'UPDATE customers SET debt = debt + ? WHERE id = ?', (data['total'], data['customerId']))
            
        # Reduce product stock
        for item in data['items']:
            execute_query(cursor, 'UPDATE products SET stock = stock - ? WHERE id = ?', (item['qty'], item['id']))
            
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 400
    finally:
        conn.close()

# API: Reset History (Delete Sales)
@app.route('/api/sales/reset', methods=['POST'])
def reset_sales():
    conn = get_db()
    cursor = conn.cursor()
    execute_query(cursor, 'DELETE FROM sales')
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

# API: End Day (Archive sales for today)
@app.route('/api/sales/archive', methods=['POST'])
def archive_sales():
    data = request.json
    date_str = data.get('date')
    conn = get_db()
    cursor = conn.cursor()
    execute_query(cursor, 'UPDATE sales SET archived = 1 WHERE date LIKE ?', (f'%{date_str}%',))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/settings', methods=['POST'])
def save_settings():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    for k, v in data.items():
        if USING_POSTGRES:
            execute_query(cursor, 'INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value', (k, str(v)))
        else:
            execute_query(cursor, 'INSERT OR REPLACE INTO settings VALUES (?, ?)', (k, str(v)))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

def startup_init():
    # Update sales schema to include archived if not exists
    conn = get_db()
    cursor = conn.cursor()
    try:
        if USING_POSTGRES:
            try:
                execute_query(cursor, 'ALTER TABLE sales ADD COLUMN archived INTEGER DEFAULT 0')
                conn.commit()
            except Exception:
                conn.rollback()
        else:
            execute_query(cursor, 'ALTER TABLE sales ADD COLUMN archived INTEGER DEFAULT 0')
            conn.commit()
    except sqlite3.OperationalError:
        pass # Column already exists
    conn.close()
    
    init_db()
    
    # Download SheetJS library if not exists
    libs_dir = 'libs'
    if not os.path.exists(libs_dir):
        os.makedirs(libs_dir)
    xlsx_path = os.path.join(libs_dir, 'xlsx.full.min.js')
    if not os.path.exists(xlsx_path) or os.path.getsize(xlsx_path) == 0:
        try:
            print("Downloading xlsx.full.min.js from cdnjs...")
            url = 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js'
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                with open(xlsx_path, 'wb') as f:
                    f.write(response.read())
            print("Download complete!")
        except Exception as e:
            print(f"Download failed: {e}")
            if not os.path.exists(xlsx_path):
                with open(xlsx_path, 'w') as f:
                    f.write('')

# Run initialization immediately when module loads
startup_init()

if __name__ == '__main__':
    # Run the server directly (for local testing)
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
