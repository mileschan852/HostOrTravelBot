import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_conn():
    return psycopg2.connect(os.getenv('DATABASE_URL'))

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS parties(
        id SERIAL PRIMARY KEY,
        host_id BIGINT NOT NULL,
        host_username VARCHAR(32),
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP NOT NULL,
        cost NUMERIC NOT NULL,
        area VARCHAR(50) NOT NULL
    )
    """)
    conn.commit()
    cur.close()
    conn.close()

def add_party(host_id, host_username, start_time, end_time, cost, area):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    INSERT INTO parties (host_id, host_username, start_time, end_time, cost, area)
    VALUES (%s, %s, %s, %s, %s, %s)
    """, (host_id, host_username, start_time, end_time, cost, area))
    conn.commit()
    cur.close()
    conn.close()

def get_upcoming_parties():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    SELECT id, host_username, start_time, end_time, cost, area 
    FROM parties 
    WHERE end_time > NOW() 
    ORDER BY start_time
    """)
    parties = cur.fetchall()
    cur.close()
    conn.close()
    return parties

def delete_expired_events():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM parties WHERE end_time < NOW()")
    conn.commit()
    cur.close()
    conn.close()