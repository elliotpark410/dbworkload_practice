import datetime as dt          # For handling dates and times
import psycopg                # PostgreSQL database adapter
import random                 # For generating random choices
import uuid                   # For generating unique IDs

class Library:
    def __init__(self, args: dict):
        # Initialize the Library object with configuration
        # Convert read_pct from percentage to decimal (default 70%)
        self.read_pct: float = float(args.get("read_pct", 70) / 100)

        # Set action type for books (BORROW, RETURN, or QUERY) - use random if not specified
        self.action: str = random.choice(["BORROW", "RETURN", "QUERY"]) if not args.get("action", "") else args["action"]

        # Generate unique IDs for books and members
        self.book_id: uuid.UUID = uuid.uuid4()
        self.member_id: uuid.UUID = uuid.uuid4()

        # Initialize timestamp and event type as empty
        self.ts: dt.datetime = ""
        self.event: str = ""

    def setup(self, conn: psycopg.Connection, id: int, total_thread_count: int):
        # Set up database connection and print debug information
        with conn.cursor() as cur:
            print(f"Library thread ID is {id}. Total thread count: {total_thread_count}")
            # Print PostgreSQL version
            print(cur.execute("SELECT version()").fetchone()[0])

    def loop(self):
        # Decide which operation to perform based on read_pct
        # If random number is less than read_pct, do a query
        # Otherwise, return both borrow and return operations
        if random.random() < self.read_pct:
            return [self.query_book]
        return [self.borrow_book, self.return_book]

    def query_book(self, conn: psycopg.Connection):
        # Query for a book in the database by its ID
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM books WHERE id = %s",
                (self.book_id,)
            )
            cur.fetchone()

    def borrow_book(self, conn: psycopg.Connection):
        # Handle book borrowing process
        # Generate new IDs for book and member
        self.book_id = uuid.uuid4()
        self.member_id = uuid.uuid4()
        self.ts = dt.datetime.now()
        self.event = "BORROW"

        with conn.cursor() as cur:
            # Record the borrowing transaction
            stmt = "INSERT INTO transactions (book_id, member_id, action, timestamp) VALUES (%s, %s, %s, %s);"
            cur.execute(stmt, (self.book_id, self.member_id, self.event, self.ts))
            # Update book status to unavailable
            cur.execute("UPDATE books SET available = FALSE WHERE id = %s", (self.book_id,))

    def return_book(self, conn: psycopg.Connection):
        # Handle book return process
        self.ts = dt.datetime.now()
        self.event = "RETURN"

        # Use a transaction to ensure data consistency
        with conn.transaction() as tx:
            with conn.cursor() as cur:
                # Check the last transaction for this book
                cur.execute(
                    "SELECT * FROM transactions WHERE book_id = %s ORDER BY timestamp DESC LIMIT 1",
                    (self.book_id,)
                )
                last_transaction = cur.fetchone()

                # Only process return if the book was previously borrowed
                if last_transaction and last_transaction[2] == "BORROW":
                    # Record the return transaction
                    stmt = "INSERT INTO transactions (book_id, member_id, action, timestamp) VALUES (%s, %s, %s, %s);"
                    cur.execute(stmt, (self.book_id, self.member_id, self.event, self.ts))
                    # Update book status to available
                    cur.execute("UPDATE books SET available = TRUE WHERE id = %s", (self.book_id,))