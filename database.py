import aiosqlite
from config import DB_PATH

CREATE_OFFERS = """
CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    price TEXT,
    photo_id TEXT,
    is_active INTEGER DEFAULT 1
)
"""

CREATE_ORDERS = """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    full_name TEXT,
    offer_id INTEGER,
    contact TEXT,
    comment TEXT,
    status TEXT DEFAULT 'new',
    created_at TEXT DEFAULT (datetime('now'))
)
"""

CREATE_CART = """
CREATE TABLE IF NOT EXISTS cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    offer_id INTEGER NOT NULL,
    added_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, offer_id)
)
"""

CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_OFFERS)
        await db.execute(CREATE_ORDERS)
        await db.execute(CREATE_CART)
        await db.execute(CREATE_SETTINGS)
        await db.commit()


async def add_offer(title: str, description: str, price: str, photo_id: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO offers (title, description, price, photo_id) VALUES (?, ?, ?, ?)",
            (title, description, price, photo_id),
        )
        await db.commit()
        return cur.lastrowid


async def get_active_offers():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM offers WHERE is_active = 1 ORDER BY id DESC")
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_all_offers():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM offers ORDER BY id DESC")
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_offer(offer_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM offers WHERE id = ?", (offer_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def delete_offer(offer_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM offers WHERE id = ?", (offer_id,))
        await db.commit()


async def toggle_offer(offer_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT is_active FROM offers WHERE id = ?", (offer_id,))
        row = await cur.fetchone()
        if not row:
            return None
        new_val = 0 if row["is_active"] else 1
        await db.execute("UPDATE offers SET is_active = ? WHERE id = ?", (new_val, offer_id))
        await db.commit()
        return new_val


async def create_order(user_id: int, username: str, full_name: str, offer_id: int, contact: str, comment: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO orders (user_id, username, full_name, offer_id, contact, comment) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username, full_name, offer_id, contact, comment),
        )
        await db.commit()
        return cur.lastrowid


# --- Корзина ---

async def add_to_cart(user_id: int, offer_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO cart (user_id, offer_id) VALUES (?, ?)",
            (user_id, offer_id),
        )
        await db.commit()


async def get_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """
            SELECT offers.* FROM cart
            JOIN offers ON offers.id = cart.offer_id
            WHERE cart.user_id = ?
            ORDER BY cart.id
            """,
            (user_id,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def remove_from_cart(user_id: int, offer_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM cart WHERE user_id = ? AND offer_id = ?", (user_id, offer_id)
        )
        await db.commit()


async def clear_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
        await db.commit()


# --- Настройки (например, статус занятости) ---

async def get_setting(key: str, default: str = "") -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cur.fetchone()
        return row["value"] if row else default


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()
