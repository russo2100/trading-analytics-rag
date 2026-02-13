import sqlite3

conn = sqlite3.connect('data/metadata.db')
cur = conn.cursor()

# Запрос данных сессии 30 января
cur.execute('SELECT session_id, total_trades, final_pnl_pct FROM sessions WHERE session_id="20260130"')
result = cur.fetchone()
print(f"Session 20260130: {result}")

# Запрос всех сессий
cur.execute('SELECT session_id, total_trades, final_pnl_pct FROM sessions')
all_sessions = cur.fetchall()
print(f"\nAll sessions:")
for row in all_sessions:
    print(f"  {row}")

conn.close()
