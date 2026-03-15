import os
from main import PostgresDB

def main():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("DATABASE_URL environment variable is required.")
        return

    print("Initializing PostgresDB connection for schema setup...")
    db = PostgresDB(db_url)
    print("Running schema creation...")
    # Call _ensure_schema explicitly since we removed it from __init__
    db._ensure_schema()
    print("Schema setup complete.")

if __name__ == "__main__":
    main()
