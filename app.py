from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATABASE = 'db.sqlite'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Initialize the database with image_url for products
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_type TEXT NOT NULL,
        name TEXT NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')

    # Products table with quantity and image_url columns
    cursor.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        farmer_name TEXT NOT NULL,
        farmer_details TEXT,
        image_url TEXT
    )''')

    # Orders table
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        status TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    )''')
    
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_type = request.form['user_type']
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']

        try:
            conn = get_db_connection()
            conn.execute('INSERT INTO users (user_type, name, username, password) VALUES (?, ?, ?, ?)',
                         (user_type, name, username, password))
            conn.commit()
            conn.close()
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists. Please choose another one.')
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['user_type'] = user['user_type']
            session['user_name'] = user['name']
            flash('Login successful!')
            return redirect(url_for('farmer' if user['user_type'] == 'farmer' else 'customer'))
        else:
            flash('Invalid username or password.')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/farmer', methods=['GET', 'POST'])
def farmer():
    if 'user_id' not in session or session['user_type'] != 'farmer':
        return redirect(url_for('login'))

    conn = get_db_connection()

    if request.method == 'POST':
        product_name = request.form.get('product_name')
        product_price = request.form.get('product_price')
        product_quantity = request.form.get('product_quantity')

        if product_name and product_price and product_quantity:
            farmer_id = session['user_id']
            conn.execute('INSERT INTO products (name, price, quantity, farmer_id) VALUES (?, ?, ?, ?)', 
                         (product_name, product_price, product_quantity, farmer_id))
            conn.commit()
            flash('Product added successfully.')
        else:
            flash('Please fill in all fields.')

    products = conn.execute('SELECT products.*, users.name AS farmer_name FROM products JOIN users ON products.farmer_id = users.id WHERE farmer_id = ?', (session['user_id'],)).fetchall()
    conn.close()
    return render_template('farmer.html', products=products, user_name=session['user_name'])

@app.route('/customer', methods=['GET', 'POST'])
def customer():
    if 'user_id' not in session or session['user_type'] != 'customer':
        return redirect(url_for('login'))

    conn = get_db_connection()
    filter_category = request.form.get('filter_category', 'all')

    if filter_category == 'all':
        products = conn.execute('SELECT products.*, users.name AS farmer_name FROM products JOIN users ON products.farmer_id = users.id').fetchall()
    else:
        products = conn.execute('SELECT products.*, users.name AS farmer_name FROM products JOIN users ON products.farmer_id = users.id WHERE products.name = ?', (filter_category,)).fetchall()

    categories = conn.execute('SELECT DISTINCT name FROM products').fetchall()
    conn.close()
    return render_template('customer.html', products=products, user_name=session['user_name'], categories=categories, filter_category=filter_category)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({'message': 'You need to be logged in to add items to your cart.'}), 403

    product_id = request.form['product_id']
    quantity = int(request.form['quantity'])
    conn = get_db_connection()
    
    product = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    
    if product:
        total = product['price'] * quantity
        
        if quantity > product['quantity']:
            return jsonify({'message': f'Insufficient stock for {product["name"]}. Available: {product["quantity"]} kg.'}), 400

        conn.execute('INSERT INTO orders (user_id, product_id, quantity, total) VALUES (?, ?, ?, ?)', 
                     (session['user_id'], product_id, quantity, total))
        conn.commit()
        
        conn.execute('UPDATE products SET quantity = quantity - ? WHERE id = ?', (quantity, product_id))
        conn.commit()
        
        flash(f'Added {quantity} kg of {product["name"]} to cart!')
        return jsonify({'message': f'Added {quantity} kg of {product["name"]} to cart!'}), 200
    else:
        return jsonify({'message': 'Product not found.'}), 404

@app.route('/cart', methods=['GET'])
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    user_id = session['user_id']
    
    orders = conn.execute('SELECT orders.*, products.name AS product_name FROM orders JOIN products ON orders.product_id = products.id WHERE orders.user_id = ?', (user_id,)).fetchall()
    total = sum(order['total'] for order in orders)  # Calculate total for the bill
    conn.close()
    
    return render_template('cart.html', orders=orders, total=total, user_name=session['user_name'])

@app.route('/delete_from_cart/<int:order_id>', methods=['POST'])
def delete_from_cart(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    order = conn.execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    
    if order:
        # Increase the product quantity back
        conn.execute('UPDATE products SET quantity = quantity + ? WHERE id = ?', (order['quantity'], order['product_id']))
        conn.commit()
        
        # Delete the order
        conn.execute('DELETE FROM orders WHERE id = ?', (order_id,))
        conn.commit()

        flash('Item deleted from cart successfully.')
    else:
        flash('Order not found.')

    return redirect(url_for('cart'))

@app.route('/process_checkout', methods=['POST'])
def process_checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Get form data
    name = request.form.get('name')
    address = request.form.get('address')
    phone = request.form.get('phone')
    payment_method = request.form.get('payment_method')

    conn = get_db_connection()
    user_id = session['user_id']

    # Fetching orders for the user
    orders = conn.execute('SELECT * FROM orders WHERE user_id = ?', (user_id,)).fetchall()

    if orders:
        # Convert orders to a list of dictionaries
        order_list = [dict(order) for order in orders]  # Convert Row to dict

        # Calculate total amount
        total_amount = sum(order['total'] for order in order_list)

        # Clear the cart by deleting all orders for this user
        conn.execute('DELETE FROM orders WHERE user_id = ?', (user_id,))
        conn.commit()

        # Store customer details in session for the bill
        session['customer_details'] = {
            'name': name,
            'address': address,
            'phone': phone,
            'payment_method': payment_method,
            'total_amount': total_amount,
            'orders': order_list  # Store as a list of dicts
        }

        flash('Thank you for your purchase! Your order has been placed.')
        
        # Redirect to the checkout page to display the bill
        return redirect(url_for('checkout'))
    else:
        flash('Your cart is empty.')
        return redirect(url_for('cart'))


@app.route('/checkout', methods=['GET'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Fetch the customer details and orders from the session
    customer_details = session.get('customer_details', None)
    orders = session.get('orders', [])  # Ensure this key matches the one you used to store orders
    total_amount = sum(order['total'] for order in orders)  # Calculate total amount

    if not customer_details or not orders:
        flash('No recent order found. Please add items to your cart.')
        return redirect(url_for('cart'))

    return render_template('checkout.html', customer_details=customer_details, orders=orders, total=total_amount)



@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'user_id' not in session or session['user_type'] != 'farmer':
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
    conn.commit()
    conn.close()
    flash('Product deleted successfully.')
    return redirect(url_for('farmer'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
