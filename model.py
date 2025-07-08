import sqlite3

def init_db():
    conn = sqlite3.connect('db.sqlite')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_type TEXT NOT NULL,
        name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')
    
    # Create products table with quantity column
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        quantity INTEGER NOT NULL,  -- Quantity in kilograms
        farmer_id INTEGER,
        FOREIGN KEY (farmer_id) REFERENCES users (id)
    )''')
    
    # Create orders table with user_id and additional customer info
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        total REAL,
        address TEXT,  -- Added address column
        phone TEXT,    -- Added phone column
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    )''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
