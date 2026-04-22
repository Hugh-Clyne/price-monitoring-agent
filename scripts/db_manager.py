import os
import sqlite3

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
    conn.row_factory = sqlite3.Row
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
            CREATE TABLE IF NOT EXISTS monitoring_settings(
            setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL UNIQUE,
            alert_email TEXT NOT NULL,
            check_frequency TEXT NOT NULL,
            alert_threshold_pct REAL NOT NULL DEFAULT 5,
            last_checked_at DATETIME,
            next_check_at DATETIME,
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
        return [dict(row) for row in c.fetchall()]

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
        WHERE cust_id = ? AND company_name = ? AND website = ?
        """, (cust_id, company_name, website))
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

def get_price_history(product_id, limit=30):
    """
    Returns price history for a product, oldest to newest.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT captured_at, price, currency, source
            FROM prices
            WHERE product_id = ?
            ORDER BY captured_at ASC
            LIMIT ?
        """, (product_id, limit))
        rows = c.fetchall()
        return [dict(row) for row in rows]

def get_previous_price(product_id):
    """
    Returns the second most recent price row for a product.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT price, currency, captured_at, source
            FROM prices
            WHERE product_id = ?
            ORDER BY captured_at DESC
            LIMIT 1 OFFSET 1
        """, (product_id,))
        row = c.fetchone()
        return dict(row) if row else None

def add_notification(product_id, old_price, new_price, percentage_change, recipient_email, subject, body):
    """
    Logs a sent notification to the database.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO notifications (product_id, old_price, new_price, percentage_change, recipient_email, subject, body)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (product_id, old_price, new_price, percentage_change, recipient_email, subject, body))
        return c.lastrowid

def get_recent_notifications(limit=20):
    """
    Returns recent notification history with product name included.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT n.notification_id, n.product_id, p.product_name, n.old_price, n.new_price, n.percentage_change,
                   n.recipient_email, n.subject, n.body, n.sent_at
            FROM notifications n
            JOIN products p ON n.product_id = p.product_id
            ORDER BY n.sent_at DESC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        return [dict(row) for row in rows]

def get_product_dashboard_rows():
    """
    Returns one row per active product with company info and latest/previous price data.
    Good for UI tables and enrichment
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT
                p.product_id,
                p.product_name,
                p.product_url,
                p.is_active,
                co.company_id,
                co.company_name,
                co.website
            FROM products p
            JOIN companies co
                ON p.company_id = co.company_id
            WHERE p.is_active = 1
            ORDER BY co.company_name, p.product_name
        """)
        products = c.fetchall()

        results = []

        for row in products:
            product_id = row["product_id"]

            c.execute("""
                SELECT price, currency, captured_at, source
                FROM prices
                WHERE product_id = ?
                ORDER BY captured_at DESC
                LIMIT 2
            """, (product_id,))
            price_rows = c.fetchall()

            latest = dict(price_rows[0]) if len(price_rows) >= 1 else None
            previous = dict(price_rows[1]) if len(price_rows) >= 2 else None

            latest_price = latest["price"] if latest else None
            previous_price = previous["price"] if previous else None

            change = None
            pct_change = None

            if latest_price is not None and previous_price is not None:
                change = latest_price - previous_price
                if previous_price != 0:
                    pct_change = (change / previous_price) * 100

            results.append({
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "product_url": row["product_url"],
                "company_id": row["company_id"],
                "company_name": row["company_name"],
                "website": row["website"],
                "latest_price": latest_price,
                "previous_price": previous_price,
                "change": change,
                "pct_change": pct_change,
                "currency": latest["currency"] if latest else None,
                "last_checked": latest["captured_at"] if latest else None,
                "source": latest["source"] if latest else None,
            })

        return results

def add_price_at_time(product_id, price, currency=None, source=None, captured_at=None):
    """
    Adds a price row with an optional custom timestamp.
    Useful for testing charts and history.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO prices (product_id, price, currency, source, captured_at)
            VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
        """, (product_id, price, currency, source, captured_at))
        return c.lastrowid

def upsert_monitoring_settings(product_id, alert_email, check_frequency, alert_threshold_pct, next_check_at):
    """
    Inserts or updates monitoring settings for a product.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO monitoring_settings (
                product_id, alert_email, check_frequency, alert_threshold_pct, next_check_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(product_id) DO UPDATE SET
                alert_email = excluded.alert_email,
                check_frequency = excluded.check_frequency,
                alert_threshold_pct = excluded.alert_threshold_pct,
                next_check_at = excluded.next_check_at
        """, (product_id, alert_email, check_frequency, alert_threshold_pct, next_check_at))

def get_monitoring_settings(product_id):
    """
    Returns monitoring settings for a product.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT *
            FROM monitoring_settings
            WHERE product_id = ?
        """, (product_id,))
        row = c.fetchone()
        return dict(row) if row else None

def get_all_monitoring_settings():
    """
    Returns all monitoring settings keyed by product_id.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT *
            FROM monitoring_settings
        """)
        rows = c.fetchall()
        return {row["product_id"]: dict(row) for row in rows}

def update_last_checked(product_id, next_check_at):
    """
    Updates last_checked_at and next_check_at after a run.
    """
    with get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE monitoring_settings
            SET last_checked_at = CURRENT_TIMESTAMP,
                next_check_at = ?
            WHERE product_id = ?
        """, (next_check_at, product_id))

if __name__ == "__main__":
    create_db()
    print("DB setup complete.")
    print(get_product_dashboard_rows())

