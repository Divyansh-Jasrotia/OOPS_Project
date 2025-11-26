# backend/db.py
import mysql.connector
from mysql.connector import Error

class DB:
    def __init__(self):
        self.conn = mysql.connector.connect(
            host="localhost",
            user="root",      
            password="Krish@1709#1610",  
            database="habit_db"
        )
        self.cursor = self.conn.cursor(dictionary=True)

    def execute(self, query, params=None):
        self.cursor.execute(query, params or ())
        self.conn.commit()

    def query(self, query, params=None, fetchone=False):
        self.cursor.execute(query, params or ())
        if fetchone:
            return self.cursor.fetchone()
        return self.cursor.fetchall()
