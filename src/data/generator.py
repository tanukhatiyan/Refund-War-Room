"""
Refund War Room - Dataset Generator.
Generates SQLite database with 500+ realistic synthetic records across orders and refunds,
plus saves documents corpus to data/documents.json.
"""
import json
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any

from src.config import DATA_DIR, DB_PATH, DOCS_PATH, ALLOWLISTED_SELLERS
from src.data.documents import DOCUMENTS


def get_db_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Path = DB_PATH):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = get_db_connection(db_path)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE sellers (
        seller_id TEXT PRIMARY KEY,
        seller_name TEXT NOT NULL,
        seller_phone TEXT NOT NULL,
        rating REAL NOT NULL,
        is_verified INTEGER NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE orders (
        order_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        customer_phone TEXT NOT NULL,
        seller_id TEXT NOT NULL,
        item_category TEXT NOT NULL,
        item_name TEXT NOT NULL,
        order_amount REAL NOT NULL,
        order_date TEXT NOT NULL,
        delivery_date TEXT,
        order_status TEXT NOT NULL,
        FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
    );
    """)

    cur.execute("""
    CREATE TABLE refunds (
        refund_id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        refund_amount REAL NOT NULL,
        request_date TEXT NOT NULL,
        refund_status TEXT NOT NULL,
        reason TEXT NOT NULL,
        seller_approval_status TEXT NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
    );
    """)

    cur.execute("""
    CREATE TABLE support_tickets (
        ticket_id TEXT PRIMARY KEY,
        order_id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        subject TEXT NOT NULL,
        message TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (order_id) REFERENCES orders(order_id)
    );
    """)

    conn.commit()
    conn.close()


def generate_dataset(db_path: Path = DB_PATH, docs_path: Path = DOCS_PATH, seed: int = 42):
    random.seed(seed)
    init_db(db_path)

    # 1. Save documents corpus to json
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(docs_path, "w", encoding="utf-8") as f:
        json.dump(DOCUMENTS, f, indent=2, ensure_ascii=False)

    conn = get_db_connection(db_path)
    cur = conn.cursor()

    # 2. Insert sellers
    seller_rows = []
    for sid, sdata in ALLOWLISTED_SELLERS.items():
        seller_rows.append((
            sid,
            sdata["name"],
            sdata["phone"],
            round(random.uniform(4.0, 4.9), 1),
            1 if sdata["verified"] else 0,
        ))
    # Add an unverified seller
    seller_rows.append(("SEL-999", "Rogue Dropshipper", "+1-800-MALICIOUS", 1.8, 0))

    cur.executemany(
        "INSERT INTO sellers VALUES (?, ?, ?, ?, ?)",
        seller_rows
    )

    # 3. Insert Key Deterministic Orders for Evaluation Questions
    deterministic_orders = [
        # ORD-1001: Electronics in 2024, opened box, within 4 days (replacement only under POL-001-v2)
        ("ORD-1001", "CUST-101", "Aarav Gupta", "+91-9811122233", "SEL-101", "Electronics", "OnePlus 12 5G", 64999.0, "2024-02-01", "2024-02-05", "DELIVERED"),
        # ORD-1002: Electronics in 2024, Dell laptop, damaged screen reported in 24h, Hinglish ticket #8821
        ("ORD-1002", "CUST-201", "Rahul Sharma", "+91-9822233344", "SEL-101", "Electronics", "Dell XPS 15 Laptop", 65000.0, "2024-03-08", "2024-03-12", "DELIVERED"),
        # ORD-1003: Electronics in 2023 (effective under POL-001-v1 30-day window)
        ("ORD-1003", "CUST-103", "Ananya Singh", "+91-9833344455", "SEL-101", "Electronics", "Sony WH-1000XM4 Headphones", 19990.0, "2023-11-15", "2023-11-20", "DELIVERED"),
        # ORD-1004: Electronics in 2024 requested return after 21 days (past 14-day window under POL-001-v2)
        ("ORD-1004", "CUST-104", "Rohan Mehta", "+91-9844455566", "SEL-101", "Electronics", "Samsung Galaxy Tab S9", 42999.0, "2024-01-10", "2024-01-15", "DELIVERED"),
        # ORD-1015: Apparel, wrong size small instead of large, tags intact, ticket #8845
        ("ORD-1015", "CUST-205", "Priya Patel", "+91-9855566677", "SEL-102", "Apparel", "Leather Biker Jacket", 3499.0, "2024-03-05", "2024-03-10", "DELIVERED"),
        # ORD-1016: Apparel, tags removed by customer
        ("ORD-1016", "CUST-106", "Kavita Reddy", "+91-9866677788", "SEL-102", "Apparel", "Silk Evening Gown", 8999.0, "2024-03-02", "2024-03-07", "DELIVERED"),
        # ORD-1020: Furniture in transit damage, seller SEL-106 claims 20% restocking fee conflict
        ("ORD-1020", "CUST-107", "Vikram Malhotra", "+91-9877788899", "SEL-106", "Furniture", "Solid Teak Dining Table", 22000.0, "2024-02-18", "2024-02-22", "DELIVERED"),
        # ORD-1030: Grocery spoiled on arrival, reported in 3 hours
        ("ORD-1030", "CUST-108", "Sunita Nair", "+91-9888899900", "SEL-103", "Grocery", "Organic Greek Yogurt & Berries", 850.0, "2024-03-01", "2024-03-01", "DELIVERED"),
        # ORD-1035: Grocery changed mind, requested 3 days later
        ("ORD-1035", "CUST-109", "Deepak Joshi", "+91-9899900011", "SEL-103", "Grocery", "Imported Washington Apples Pack", 450.0, "2024-03-02", "2024-03-03", "DELIVERED"),
        # ORD-1042: Double charged order, UPI ticket #8890
        ("ORD-1042", "CUST-218", "Aman Verma", "+91-9812345678", "SEL-101", "Electronics", "Wireless Bluetooth Speaker", 2499.0, "2024-03-18", "2024-03-21", "DELIVERED"),
        # ORD-1050: Watches, counterfeit claim with certificate
        ("ORD-1050", "CUST-111", "Manish Kapoor", "+91-9823456789", "SEL-104", "Watches", "Designer Chronograph Watch", 18500.0, "2024-02-12", "2024-02-16", "DELIVERED"),
        # ORD-1055: Luxury Watch (Omega Speedmaster), missing SLA fields in POL-005
        ("ORD-1055", "CUST-112", "Siddharth Sen", "+91-9834567890", "SEL-104", "Watches", "Omega Speedmaster Chronograph", 320000.0, "2024-03-05", "2024-03-10", "DELIVERED"),
        # ORD-1060: Delayed order (promised 2024-02-10, delivered 2024-02-18, 8 days delay)
        ("ORD-1060", "CUST-113", "Neha Sharma", "+91-9845678901", "SEL-102", "Apparel", "Winter Cashmere Overcoat", 12499.0, "2024-02-01", "2024-02-18", "DELIVERED"),
    ]

    cur.executemany(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        deterministic_orders
    )

    # 4. Deterministic Refunds
    deterministic_refunds = [
        ("REF-5001", "ORD-1001", 64999.0, "2024-02-09", "REJECTED_REFUND_REPLACEMENT_OFFERED", "Defective Screen", "APPROVED"),
        ("REF-5002", "ORD-1002", 65000.0, "2024-03-13", "PENDING_OPS_MANAGER_APPROVAL", "Damaged in transit", "REJECTED"),
        ("REF-5003", "ORD-1003", 19990.0, "2023-12-10", "PROCESSED", "Sound distortion", "APPROVED"),
        ("REF-5004", "ORD-1004", 42999.0, "2024-02-05", "REJECTED_EXPIRED_WINDOW", "Changed mind", "REJECTED"),
        ("REF-5005", "ORD-1015", 3499.0, "2024-03-14", "APPROVED", "Size mismatch - sent Small instead of Large", "APPROVED"),
        ("REF-5006", "ORD-1020", 22000.0, "2024-02-23", "DISPUTED", "Cracked tabletop in transit", "DISPUTED_RESTOCKING_FEE"),
        ("REF-5007", "ORD-1030", 850.0, "2024-03-01", "PROCESSED_WALLET_CREDIT", "Spoiled dairy products on delivery", "APPROVED"),
        ("REF-5008", "ORD-1035", 450.0, "2024-03-05", "REJECTED_NON_RETURNABLE", "Customer changed mind", "REJECTED"),
        ("REF-5009", "ORD-1050", 18500.0, "2024-02-20", "PROCESSED_WITH_GOODWILL", "Counterfeit verified by brand center", "REJECTED"),
    ]

    cur.executemany(
        "INSERT INTO refunds VALUES (?, ?, ?, ?, ?, ?, ?)",
        deterministic_refunds
    )

    # 5. Deterministic Support Tickets
    deterministic_tickets = [
        ("TCK-8821", "ORD-1002", "CUST-201", "Screen Damage Complaint",
         "Mera order ORD-1002 deliver hua tha 12 March ko. Screen completely damaged aur flickering aaya tha. Seller SEL-101 se contact kiya toh seller bola replacement nahi milega kyunki box khol diya. Maine 24 hours ke andar complain kiya tha photo ke sath. Please mera full refund kara do urgent, bohot pareshaan hu.",
         "ESCALATED", "2024-03-12 14:22:00"),
        ("TCK-8845", "ORD-1015", "CUST-205", "Size Mismatch Complaint",
         "Order ORD-1015 maine Large size order kiya tha lekin packet me Small size bheja hai. Brand tag and barcode tag bilkul intact attached hai, kapda pehna bhi nahi. Refund status check karo aur pick up arrange karwa do.",
         "RESOLVED", "2024-03-14 10:15:00"),
        ("TCK-8890", "ORD-1042", "CUST-218", "Double Charge Glitch Query",
         "Order ORD-1042 ke waqt UPI se do baar payment kat gaya (INR 2499 x 2). Ek order confirm ho gaya, dusra debited amount ka refund kab tak aayega bank account me? UPI reference number 99482012487.",
         "OPEN", "2024-03-18 16:45:00"),
        ("TCK-8899", "ORD-1020", "CUST-107", "Seller charging restocking fee dispute",
         "Seller SEL-106 is refusing 100% refund for damaged dining table and demanding a 20% restocking fee deduction. Please intervene under platform damage protection policy.",
         "ESCALATED", "2024-02-23 09:30:00"),
    ]

    cur.executemany(
        "INSERT INTO support_tickets VALUES (?, ?, ?, ?, ?, ?, ?)",
        deterministic_tickets
    )

    # 6. Generate 550+ Synthetic Orders and Refunds to reach 600 total records
    categories = {
        "Electronics": ["SEL-101"],
        "Apparel": ["SEL-102"],
        "Grocery": ["SEL-103"],
        "Watches": ["SEL-104"],
        "Cosmetics": ["SEL-105"],
        "Furniture": ["SEL-106"],
    }
    
    items = {
        "Electronics": [("Wireless Mouse", 1299.0), ("Mechanical Keyboard", 4599.0), ("USB-C Dock", 2999.0), ("Noise Cancelling Earbuds", 5999.0), ("4K Monitor", 24999.0), ("Smartwatch Band", 899.0)],
        "Apparel": [("Cotton Crewneck T-Shirt", 799.0), ("Slim Fit Denim Jeans", 1999.0), ("Running Sneakers", 3499.0), ("Formal Blazer", 6499.0), ("Linen Summer Shirt", 1499.0)],
        "Grocery": [("Organic Almonds 500g", 650.0), ("Cold Pressed Olive Oil 1L", 1200.0), ("Artisanal Coffee Beans 250g", 550.0), ("Raw Forest Honey 500g", 450.0)],
        "Watches": [("Minimalist Quartz Watch", 3999.0), ("Automatic Field Watch", 14999.0), ("Sports Chrono", 8999.0)],
        "Cosmetics": [("Hydrating Face Serum 30ml", 1499.0), ("Matte Liquid Lipstick", 799.0), ("Sunscreen SPF 50", 699.0), ("Eau De Parfum 100ml", 4999.0)],
        "Furniture": [("Ergonomic Mesh Office Chair", 9500.0), ("Solid Wood Bookshelf", 14000.0), ("Bedside Nightstand", 4500.0), ("Floor Standing Lamp", 3200.0)],
    }

    names = ["Aditya", "Riya", "Kunal", "Sneha", "Arjun", "Pooja", "Varun", "Meera", "Kabir", "Tanvi", "Nikhil", "Simran", "Tarun", "Divya", "Gaurav", "Isha"]
    surnames = ["Kapoor", "Iyer", "Rao", "Chopra", "Das", "Menon", "Bose", "Saxena", "Deshmukh", "Nambiar", "Banerjee", "Bhat"]

    start_date = datetime(2023, 6, 1)

    generated_orders = []
    generated_refunds = []
    generated_tickets = []

    order_counter = 1100
    refund_counter = 5100
    ticket_counter = 9000

    for i in range(550):
        cat = random.choice(list(categories.keys()))
        seller = random.choice(categories[cat])
        item_name, base_price = random.choice(items[cat])
        price = round(base_price * random.uniform(0.9, 1.2), 2)
        
        c_name = f"{random.choice(names)} {random.choice(surnames)}"
        c_id = f"CUST-{random.randint(1000, 9999)}"
        c_phone = f"+91-9{random.randint(100000000, 999999999)}"

        order_dt = start_date + timedelta(days=random.randint(0, 290))
        deliv_dt = order_dt + timedelta(days=random.randint(2, 6))
        status = random.choices(["DELIVERED", "SHIPPED", "RETURN_REQUESTED", "REFUNDED", "CANCELLED"], weights=[70, 10, 10, 8, 2])[0]
        
        oid = f"ORD-{order_counter}"
        order_counter += 1

        deliv_str = deliv_dt.strftime("%Y-%m-%d") if status != "CANCELLED" else None
        generated_orders.append((
            oid, c_id, c_name, c_phone, seller, cat, item_name, price,
            order_dt.strftime("%Y-%m-%d"), deliv_str, status
        ))

        # Create refunds for ~40% of orders
        if status in ["RETURN_REQUESTED", "REFUNDED"] or random.random() < 0.25:
            ref_dt = (deliv_dt + timedelta(days=random.randint(1, 20))).strftime("%Y-%m-%d")
            ref_status = random.choice(["PROCESSED", "APPROVED", "REJECTED", "PENDING"])
            reason = random.choice(["Defective item", "Wrong size", "Damaged in transit", "Changed mind", "Late delivery"])
            seller_approval = random.choice(["APPROVED", "REJECTED", "PENDING"])
            rid = f"REF-{refund_counter}"
            refund_counter += 1
            
            generated_refunds.append((
                rid, oid, price, ref_dt, ref_status, reason, seller_approval
            ))

            # Sample some Hinglish & English tickets
            if random.random() < 0.3:
                tid = f"TCK-{ticket_counter}"
                ticket_counter += 1
                hinglish_templates = [
                    f"Mera order {oid} ka refund abhi tak process nahi hua, please help.",
                    f"Seller {seller} se baat kiya par koi update nahi mil raha {oid} ke liye.",
                    f"Order {oid} receive ho gaya tha par item thoda damaged lag raha tha. Kya exchange hoga?",
                    f"Package delivered dikha raha hai par mujhe nahi mila. Order id {oid}."
                ]
                english_templates = [
                    f"Inquiry regarding refund status for order {oid}.",
                    f"Requesting update on replacement for {oid}.",
                    f"Order {oid} arrived with missing parts."
                ]
                msg = random.choice(hinglish_templates + english_templates)
                generated_tickets.append((
                    tid, oid, c_id, f"Support query for {oid}", msg,
                    random.choice(["OPEN", "RESOLVED", "ESCALATED"]),
                    (deliv_dt + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
                ))

    cur.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", generated_orders)
    cur.executemany("INSERT INTO refunds VALUES (?, ?, ?, ?, ?, ?, ?)", generated_refunds)
    cur.executemany("INSERT INTO support_tickets VALUES (?, ?, ?, ?, ?, ?, ?)", generated_tickets)

    conn.commit()
    
    # Verification query
    cur.execute("SELECT count(*) FROM orders")
    order_count = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM refunds")
    refund_count = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM support_tickets")
    ticket_count = cur.fetchone()[0]
    conn.close()

    return {
        "orders_count": order_count,
        "refunds_count": refund_count,
        "tickets_count": ticket_count,
        "total_records": order_count + refund_count,
        "documents_count": len(DOCUMENTS)
    }


if __name__ == "__main__":
    stats = generate_dataset()
    print("Database and documents generated successfully:")
    print(stats)
