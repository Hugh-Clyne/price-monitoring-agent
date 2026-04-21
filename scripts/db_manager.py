import os
import sqlite3
from site_parser import safe_get, extract_data_from_html

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

def get_connection():
    """
    Makes connection to db for price monitoring agent
    """
    db_dir = os.path.join(root_dir, 'data')
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, 'price_tracker.db')

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def create_db():
    """
    Creates database for the price monitoring agent.
    """

    with get_connection() as conn:
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS customers(
                cust_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL UNIQUE
            );
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS companies(
                company_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cust_id INTEGER NOT NULL,
                company_name TEXT NOT NULL,
                website TEXT NOT NULL,
                FOREIGN KEY (cust_id) REFERENCES customers(cust_id) ON DELETE CASCADE,
                UNIQUE(cust_id, company_name, website)
            );
            """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS products(
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                product_url TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
                FOREIGN KEY (company_id) REFERENCES companies(company_id) ON DELETE CASCADE,
                UNIQUE(company_id, product_url)
            );
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS product_matches(
                match_id INTEGER PRIMARY KEY AUTOINCREMENT,
                cust_product_id INTEGER NOT NULL,
                competitor_product_id INTEGER NOT NULL,
                match_notes TEXT,
                FOREIGN KEY (cust_product_id) REFERENCES products(product_id) ON DELETE CASCADE,
                FOREIGN KEY (competitor_product_id) REFERENCES products(product_id) ON DELETE CASCADE,
                UNIQUE(cust_product_id, competitor_product_id)
            );
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS prices(
                price_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                captured_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                price REAL NOT NULL CHECK(price >= 0),
                currency TEXT CHECK(length(currency) = 3),
                source TEXT,
                FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
            );
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS notifications(
            notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            old_price REAL,
            new_price REAL,
            percentage_change REAL,
            recipient_email TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT,
            sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
            );
        """)

        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_companies_cust_id
            ON companies(cust_id);
        """)

        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_products_company_id
            ON products(company_id);
        """)

        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_prices_product_id_captured_at
            ON prices(product_id, captured_at);
        """)

        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_product_matches_cust_product_id
            ON product_matches(cust_product_id);
        """)

        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_product_matches_competitor_product_id
            ON product_matches(competitor_product_id);
        """)

def add_customer(customer_name):
    """
    Function to add new customer data.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO customers (customer_name) VALUES (?)", (customer_name,))
        if c.lastrowid:
            return c.lastrowid
        c.execute("SELECT cust_id FROM customers WHERE customer_name = ?",(customer_name,))
        return c.fetchone()[0]

def add_price(product_id,price,currency=None,source=None):
    """
    Function to add new price data."""
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO prices (product_id, price, currency, source)
            VALUES (?, ?, ?, ?)
        """, (product_id, price, currency, source))
        return c.lastrowid

def  get_active_products():
    """
    Function to get all active products.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT product_id, company_id, product_name, product_url
            FROM products
            WHERE is_active = 1
        """)
        return c.fetchall()

def add_company(cust_id, company_name, website):
    """
    Function to add new company data.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO companies (cust_id, company_name, website)
            VALUES (?, ?, ?)
        """, (cust_id, company_name, website))
        if c.lastrowid:
            return c.lastrowid
        c.execute("""
        SELECT company_id FROM companies
        WHERE cust_id = ? AND company_name = ?
        """, (cust_id, company_name))
        return c.fetchone()[0]


def add_product(company_id, product_name, product_url):
    """
    Function to add new product data.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO products (company_id, product_name, product_url)
            VALUES (?, ?, ?)
        """, (company_id, product_name, product_url))
        if c.lastrowid:
            return c.lastrowid
        c.execute("""
        SELECT product_id
        FROM products
        WHERE company_id = ? AND product_url = ?
        """, (company_id, product_url))
        return c.fetchone()[0]

def get_latest_price(product_id):
    """
    Function to get the latest price for a given product.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT price, currency, captured_at, source
            FROM prices
            WHERE product_id = ?
            ORDER BY captured_at DESC
            LIMIT 1
        """, (product_id,))
        return c.fetchone()
        
if __name__ == "__main__":
    create_db()

    cust_id = add_customer("Test Customer")
    company_id = add_company(cust_id, "Blenders Eyewear", "https://www.blenderseyewear.com")
    product_id = add_product(company_id, "Canyon Black Tundra", "https://www.blenderseyewear.com/collections/all-mens-sunglasses/products/canyon-black-tundra")

    print("DB setup complete.")

