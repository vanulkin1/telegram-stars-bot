import sqlite3
import logging

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except sqlite3.Error as e:
        logging.error(f"Error connecting to database: {e}")
    return conn


def create_tables(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            stars_bought INTEGER DEFAULT 0,
            premium_months_bought INTEGER DEFAULT 0,
            banned INTEGER DEFAULT 0
        )
    """)
    conn.commit()


def get_user_profile(db_file, user_id):
    conn = create_connection(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT username, stars_bought, premium_months_bought, banned FROM users WHERE user_id = ?",
                   (user_id,))
    result = cursor.fetchone()
    conn.close()
    if result:
        username, stars_bought, premium_months_bought, banned = result
        return {"username": username, "stars_bought": stars_bought,
                "premium_months_bought": premium_months_bought, "banned": bool(banned)}
    else:
        return {"username": None, "stars_bought": 0, "premium_months_bought": 0, "banned": False}


def update_user_profile(db_file, user_id, username, stars=0, premium_months=0):
    conn = create_connection(db_file)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (user_id, username, stars_bought, premium_months_bought) VALUES (?, ?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET username=?, stars_bought=stars_bought + ?, premium_months_bought=premium_months_bought + ?",
            (user_id, username, stars, premium_months, username, stars, premium_months),
        )
        conn.commit()
    except Exception as e:
        logging.error(f"Database update error: {e}")
    finally:
        conn.close()


def ban_user(db_file, user_id):
    conn = create_connection(db_file)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def unban_user(db_file, user_id):
    conn = create_connection(db_file)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET banned = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def get_total_users(db_file):
    conn = create_connection(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_top_spender(db_file):
    conn = create_connection(db_file)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, stars_bought + premium_months_bought FROM users ORDER BY stars_bought + premium_months_bought DESC LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0], result[1]
    else:
        return None, 0


def get_total_stars_bought(db_file):
    conn = create_connection(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(stars_bought) FROM users")
    total = cursor.fetchone()[0]
    conn.close()
    return total if total else 0


def get_all_user_ids(db_file):
    conn = create_connection(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    ids = [row[0] for row in cursor.fetchall()]
    conn.close()
    return ids
