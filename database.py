import asyncpg
import os
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL не задан. Проверьте переменные окружения.")

pool = None


async def init_db():
    """Инициализация пула подключений и создание таблиц."""
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)
    
    async with pool.acquire() as conn:
        # Offers table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS offers (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                price TEXT,
                photo_id TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Orders table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                username TEXT,
                full_name TEXT,
                offer_id INTEGER,
                contact TEXT,
                payment_method TEXT DEFAULT 'unknown',
                hosting TEXT DEFAULT 'free',
                comment TEXT,
                status TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Cart table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cart (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                offer_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, offer_id)
            )
        """)
        
        # Settings table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)


async def add_offer(title: str, description: str, price: str, photo_id: str) -> int:
    """Добавить новый оффер."""
    async with pool.acquire() as conn:
        offer_id = await conn.fetchval(
            """INSERT INTO offers (title, description, price, photo_id) 
               VALUES ($1, $2, $3, $4) RETURNING id""",
            title, description, price, photo_id
        )
        return offer_id


async def get_active_offers():
    """Получить активные офферы."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM offers WHERE is_active = 1 ORDER BY id DESC"
        )
        return [dict(r) for r in rows]


async def get_all_offers():
    """Получить все офферы."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM offers ORDER BY id DESC"
        )
        return [dict(r) for r in rows]


async def get_offer(offer_id: int):
    """Получить оффер по ID."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM offers WHERE id = $1",
            offer_id
        )
        return dict(row) if row else None


async def delete_offer(offer_id: int):
    """Удалить оффер."""
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM offers WHERE id = $1",
            offer_id
        )


async def toggle_offer(offer_id: int):
    """Переключить статус оффера (активный/неактивный)."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT is_active FROM offers WHERE id = $1",
            offer_id
        )
        if not row:
            return None
        new_val = 0 if row['is_active'] else 1
        await conn.execute(
            "UPDATE offers SET is_active = $1 WHERE id = $2",
            new_val, offer_id
        )
        return new_val


async def create_order(user_id: int, username: str, full_name: str, offer_id: int, 
                       contact: str, payment_method: str, hosting: str, comment: str) -> int:
    """Создать заказ."""
    async with pool.acquire() as conn:
        order_id = await conn.fetchval(
            """INSERT INTO orders (user_id, username, full_name, offer_id, contact, 
                                   payment_method, hosting, comment) 
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING id""",
            user_id, username, full_name, offer_id, contact, payment_method, hosting, comment
        )
        return order_id


# --- Корзина ---

async def add_to_cart(user_id: int, offer_id: int):
    """Добавить товар в корзину."""
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO cart (user_id, offer_id) VALUES ($1, $2) 
               ON CONFLICT (user_id, offer_id) DO NOTHING""",
            user_id, offer_id
        )


async def get_cart(user_id: int):
    """Получить товары в корзине пользователя."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT offers.* FROM cart
               JOIN offers ON offers.id = cart.offer_id
               WHERE cart.user_id = $1
               ORDER BY cart.id""",
            user_id
        )
        return [dict(r) for r in rows]


async def remove_from_cart(user_id: int, offer_id: int):
    """Удалить товар из корзины."""
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM cart WHERE user_id = $1 AND offer_id = $2",
            user_id, offer_id
        )


async def clear_cart(user_id: int):
    """Очистить корзину пользователя."""
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM cart WHERE user_id = $1",
            user_id
        )


# --- Настройки ---

async def get_setting(key: str, default: str = "") -> str:
    """Получить значение настройки."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT value FROM settings WHERE key = $1",
            key
        )
        return row['value'] if row else default


async def set_setting(key: str, value: str):
    """Установить значение настройки."""
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO settings (key, value) VALUES ($1, $2) 
               ON CONFLICT (key) DO UPDATE SET value = $2""",
            key, value
        )


# --- Промокоды ---

VALID_PROMO_CODES = {
    "BADG5": 5,
    "MILKA5": 5,
    "WELV5": 5,
}


async def has_orders(user_id: int) -> bool:
    """Проверить, есть ли у пользователя хотя бы один заказ."""
    async with pool.acquire() as conn:
        row = await conn.fetchval(
            "SELECT 1 FROM orders WHERE user_id = $1 LIMIT 1",
            user_id
        )
        return row is not None


async def save_user_promo(user_id: int, code: str):
    """Сохранить применённый промокод пользователя."""
    await set_setting(f"promo_{user_id}", code)


async def get_user_promo(user_id: int) -> str:
    """Получить применённый промокод пользователя."""
    return await get_setting(f"promo_{user_id}", "")


async def clear_user_promo(user_id: int):
    """Удалить применённый промокод пользователя."""
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM settings WHERE key = $1",
            f"promo_{user_id}"
        )

