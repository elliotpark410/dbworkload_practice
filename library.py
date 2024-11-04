import datetime as dt
import psycopg
import random
import uuid

class Library:
    def __init__(self, args: dict):
        """Initialize the Library workload"""
        self.read_pct: float = float(args.get("read_pct", 70) / 100)
        self.action: str = random.choice(["BORROW", "RETURN", "QUERY"]) if not args.get("action", "") else args["action"]
        self.book_id: uuid.UUID = None
        self.member_id: uuid.UUID = None
        self.ts: dt.datetime = dt.datetime.now()
        self.event: str = ""

    def get_random_book(self, cur: psycopg.Cursor, available: bool = None):
        """Get a random book ID from the database"""
        if available is None:
            cur.execute("SELECT id FROM books ORDER BY RANDOM() LIMIT 1")
        else:
            cur.execute("SELECT id FROM books WHERE available = %s ORDER BY RANDOM() LIMIT 1", (available,))
        result = cur.fetchone()
        return result[0] if result else None

    def get_random_member(self, cur: psycopg.Cursor):
        """Get a random member ID from the database"""
        cur.execute("SELECT id FROM members ORDER BY RANDOM() LIMIT 1")
        result = cur.fetchone()
        return result[0] if result else None

    def setup(self, conn: psycopg.Connection, id: int, total_thread_count: int):
        """Initialize the workload"""
        with conn.cursor() as cur:
            print(f"Library thread ID is {id}. Total thread count: {total_thread_count}")
            print(cur.execute("SELECT version()").fetchone()[0])

    def loop(self):
        """Determine which operations to perform"""
        if random.random() < self.read_pct:
            return [self.query_book]
        return [self.borrow_book, self.return_book]

    def query_book(self, conn: psycopg.Connection):
        """Read operation - query book details"""
        with conn.cursor() as cur:
            book_id = self.get_random_book(cur)
            if book_id:
                cur.execute("""
                    SELECT b.*,
                           COALESCE(t.action, 'NONE') as last_action
                    FROM books b
                    LEFT JOIN transactions t ON b.id = t.book_id
                    WHERE b.id = %s
                    ORDER BY t.timestamp DESC
                    LIMIT 1
                """, (book_id,))
                cur.fetchone()

    def borrow_book(self, conn: psycopg.Connection):
        """Write operation - borrow a book"""
        with conn.cursor() as cur:
            self.book_id = self.get_random_book(cur, available=True)
            self.member_id = self.get_random_member(cur)

            if self.book_id and self.member_id:
                self.ts = dt.datetime.now()
                self.event = "BORROW"

                stmt = "INSERT INTO transactions (book_id, member_id, action, timestamp) VALUES (%s, %s, %s, %s);"
                cur.execute(stmt, (self.book_id, self.member_id, self.event, self.ts))
                cur.execute("UPDATE books SET available = FALSE WHERE id = %s", (self.book_id,))

    def return_book(self, conn: psycopg.Connection):
        """Write operation - return a book"""
        with conn.cursor() as cur:
            # Get a borrowed book
            cur.execute("""
                SELECT t.book_id, t.member_id
                FROM transactions t
                JOIN books b ON t.book_id = b.id
                WHERE b.available = FALSE
                AND t.action = 'BORROW'
                ORDER BY t.timestamp DESC
                LIMIT 1
            """)
            result = cur.fetchone()

            if result:
                self.book_id, self.member_id = result
                self.ts = dt.datetime.now()
                self.event = "RETURN"

                stmt = "INSERT INTO transactions (book_id, member_id, action, timestamp) VALUES (%s, %s, %s, %s);"
                cur.execute(stmt, (self.book_id, self.member_id, self.event, self.ts))
                cur.execute("UPDATE books SET available = TRUE WHERE id = %s", (self.book_id,))