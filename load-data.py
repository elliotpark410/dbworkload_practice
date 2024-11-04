import psycopg
import yaml
import uuid
import random
import string
from datetime import datetime, timedelta

def generate_random_string(min_length, max_length, seed):
    """Generate a random string of given length"""
    random.seed(seed)
    length = random.randint(min_length, max_length)
    return ''.join(random.choices(string.ascii_letters + ' ', k=length)).strip()

def generate_isbn(seed):
    """Generate ISBN following pattern ###-#-##-######-#"""
    random.seed(seed)
    parts = [
        ''.join(random.choices(string.digits, k=3)),
        random.choice(string.digits),
        ''.join(random.choices(string.digits, k=2)),
        ''.join(random.choices(string.digits, k=6)),
        random.choice(string.digits)
    ]
    return '-'.join(parts)

def generate_email(seed):
    """Generate email following pattern ????##@example.com"""
    random.seed(seed)
    letters = ''.join(random.choices(string.ascii_lowercase, k=4))
    numbers = ''.join(random.choices(string.digits, k=2))
    return f"{letters}{numbers}@example.com"

def generate_date(start_date, end_date, seed):
    """Generate random date between start and end date"""
    random.seed(seed)
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    days_between = (end - start).days
    random_days = random.randint(0, days_between)
    return start + timedelta(days=random_days)

def load_test_data():
    # Connect to CockroachDB
    conn = psycopg.connect('postgresql://root@localhost:26257/library?sslmode=disable')

    try:
        # Load YAML file
        with open('library-test-data.yaml', 'r') as file:
            data = yaml.safe_load(file)

        with conn.cursor() as cur:
            # Clear existing data
            print("Clearing existing data...")
            cur.execute("TRUNCATE books, members, transactions CASCADE")

            # Insert books
            print("Inserting books...")
            books_config = data['books'][0]
            for i in range(books_config['count']):
                random.seed(i)  # Set seed for reproducibility

                cur.execute("""
                    INSERT INTO books (id, title, author, isbn, publication_year, genre, available)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    uuid.UUID(int=random.getrandbits(128)),
                    generate_random_string(
                        books_config['columns']['title']['args']['min'],
                        books_config['columns']['title']['args']['max'],
                        i + books_config['columns']['title']['args']['seed']
                    ),
                    generate_random_string(
                        books_config['columns']['author']['args']['min'],
                        books_config['columns']['author']['args']['max'],
                        i + books_config['columns']['author']['args']['seed']
                    ),
                    generate_isbn(i + books_config['columns']['isbn']['args']['seed']),
                    random.randint(
                        books_config['columns']['publication_year']['args']['min'],
                        books_config['columns']['publication_year']['args']['max']
                    ),
                    random.choice(books_config['columns']['genre']['args']['population']),
                    random.choice([True, False])
                ))

            # Insert members
            print("Inserting members...")
            members_config = data['members'][0]
            for i in range(members_config['count']):
                random.seed(i)

                cur.execute("""
                    INSERT INTO members (id, name, email, join_date, membership_type)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    uuid.UUID(int=random.getrandbits(128)),
                    generate_random_string(
                        members_config['columns']['name']['args']['min'],
                        members_config['columns']['name']['args']['max'],
                        i + members_config['columns']['name']['args']['seed']
                    ),
                    generate_email(i + members_config['columns']['email']['args']['seed']),
                    generate_date(
                        members_config['columns']['join_date']['args']['start'],
                        members_config['columns']['join_date']['args']['end'],
                        i + members_config['columns']['join_date']['args']['seed']
                    ),
                    random.choice(members_config['columns']['membership_type']['args']['population'])
                ))

            conn.commit()

            # Verify data
            cur.execute("SELECT COUNT(*) FROM books")
            books_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM members")
            members_count = cur.fetchone()[0]

            print(f"\nData loaded successfully!")
            print(f"Books inserted: {books_count}")
            print(f"Members inserted: {members_count}")

    except Exception as e:
        print(f"Error loading data: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    load_test_data()