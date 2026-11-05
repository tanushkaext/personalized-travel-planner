import os
import pymysql
from pymysql.cursors import DictCursor
from flask import g
from dotenv import load_dotenv

load_dotenv()

def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', ''),
            database=os.getenv('MYSQL_DB', 'travel_planner'),
            port=int(os.getenv('MYSQL_PORT', 3306)),
            cursorclass=DictCursor,
            autocommit=False
        )
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    conn = get_db()
    with conn.cursor() as cursor:
        cursor.execute(query, args)
        rv = cursor.fetchall()
        return (rv[0] if rv else None) if one else rv

def execute_db(query, args=(), commit=True):
    conn = get_db()
    with conn.cursor() as cursor:
        cursor.execute(query, args)
        if commit:
            conn.commit()
        return cursor.lastrowid