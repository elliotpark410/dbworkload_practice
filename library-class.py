import datetime as dt
import psycopg
import random
import time
import uuid

class Library:
    def __init__(self, args: dict):
        self.read_pct: float = float(args.get("read_pct", 70) / 100)
        self.action: str = random.choice(["BORROW", "RETURN", "QUERY"]) if not args.get("action", "") else args["action"]
        self.book_id: uuid.UUID = uuid.uuid4()
        self.member_id: uuid.UUID = uuid.uuid4()
        self.ts: dt.datetime = ""
        self.event: str = ""

    def setup(self, conn: psycopg.Connection, id: int, total_thread_count: int):
        with conn.cursor() as cur:
            print(f"Library thread ID is {id}. Total thread count: {total_thread_count}")
            print(cur.execute("SELECT version()").fetchone()[0])

    def loop(self):
        if random.random() < self.read_pct:
            return [self.query_book]
        return [self.borrow_book, self.return_book]

    def query_book(self, conn: psycopg.Connection):
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM books WHERE id = %s",
                (self.book_id,)
            )
            cur.fetchone()

    def borrow_book(self, conn: psycopg.Connection):
        self.book_id = uuid.uuid4()
        self.member_id = uuid.uuid4()
        self.ts = dt.datetime.now()
        self.event = "BORROW"
        with conn.cursor() as cur:
            stmt = "INSERT INTO transactions (book_id, member_id, action, timestamp) VALUES (%s, %s, %s, %s);"
            cur.execute(stmt, (self.book_id, self.member_id, self.event, self.ts))
            cur.execute("UPDATE books SET available = FALSE WHERE id = %s", (self.book_id,))

    def return_book(self, conn: psycopg.Connection):
        self.ts = dt.datetime.now()
        self.event = "RETURN"
        with conn.transaction() as tx:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM transactions WHERE book_id = %s ORDER BY timestamp DESC LIMIT 1",
                    (self.book_id,)
                )
                last_transaction = cur.fetchone()
                if last_transaction and last_transaction[2] == "BORROW":
                    stmt = "INSERT INTO transactions (book_id, member_id, action, timestamp) VALUES (%s, %s, %s, %s);"
                    cur.execute(stmt, (self.book_id, self.member_id, self.event, self.ts))
                    cur.execute("UPDATE books SET available = TRUE WHERE id = %s", (self.book_id,))
