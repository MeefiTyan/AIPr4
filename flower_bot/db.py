import sqlite3

def init_db():
    conn = sqlite3.connect("bouquets.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        name TEXT,
        phone TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        bouquet_type TEXT,
        quantity INTEGER,
        delivery_address TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    conn.commit()
    conn.close()

def add_user(user_id, username, name):
    conn = sqlite3.connect("bouquets.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (id, username, name) VALUES (?, ?, ?)",
                   (user_id, username, name))
    conn.commit()
    conn.close()

def add_order(user_id, bouquet_type, quantity, address):
    conn = sqlite3.connect("bouquets.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (user_id, bouquet_type, quantity, delivery_address) VALUES (?, ?, ?, ?)",
                   (user_id, bouquet_type, quantity, address))
    conn.commit()
    conn.close()

def get_orders_by_user(user_id):
    conn = sqlite3.connect("bouquets.db")
    cursor = conn.cursor()
    cursor.execute("SELECT bouquet_type, quantity, delivery_address FROM orders WHERE user_id = ?", (user_id,))
    orders = cursor.fetchall()
    conn.close()
    return orders

