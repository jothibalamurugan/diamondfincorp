import os
import sys
from dotenv import load_dotenv

# Add current directory to path so we can import models and DB if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from datetime import datetime

from main import ExcelDB, PostgresDB, EXCEL_DB_PATH

# Load environment variables
load_dotenv()

RAILWAY_DB_URL = os.environ.get('DATABASE_URL')

if not RAILWAY_DB_URL:
    print("Error: DATABASE_URL environment variable is not set. Please set it to your Railway PostgreSQL connection string.")
    print("Example: set DATABASE_URL=postgresql://postgres:...@.../railway")
    sys.exit(1)

def migrate_data():
    print("Starting migration from Excel to PostgreSQL...")
    print(f"Reading from: {EXCEL_DB_PATH}")
    print(f"Writing to: {RAILWAY_DB_URL}")
    print("-" * 50)

    try:
        # Initialize databases
        excel_db = ExcelDB(EXCEL_DB_PATH)
        pg_db = PostgresDB(RAILWAY_DB_URL)
        print("Database connections established successfully.")
    except Exception as e:
        print(f"Error connecting to databases: {e}")
        sys.exit(1)

    sheets_to_migrate = [
        'Customers',
        'Loans',
        'Payments',
        'CapitalInjections',
        'AuditLog'
    ]

    for sheet_name in sheets_to_migrate:
        print(f"\nMigrating table: {sheet_name}...")
        try:
            # 1. Fetch from Excel
            rows = excel_db.get_all_rows(sheet_name)
            print(f"Found {len(rows)} rows in Excel.")

            # 2. Convert dictionary rows back to lists to match PostgresDB.add_row
            # We need to map dict keys back to the exact list order expected by PostgresDB.add_row
            cols_map = {}
            if sheet_name == 'Customers':
                cols_map = ['customer_id', 'name', 'phone', 'email', 'address', 'id_proof_type', 'id_proof_number', 'status', 'created_date', 'notes']
            elif sheet_name == 'Loans':
                cols_map = ['loan_id', 'customer_id', 'principal_amount', 'interest_rate', 'loan_type', 'start_date', 'tenure_months', 'status', 'fund_source', 'created_date', 'closed_date', 'notes', 'transaction_type', 'original_interest_amount', 'waived_interest_amount', 'waiver_reason', 'waiver_date']
            elif sheet_name == 'Payments':
                cols_map = ['payment_id', 'loan_id', 'customer_id', 'payment_date', 'amount', 'payment_type', 'payment_method', 'reference_number', 'created_date', 'created_by', 'notes']
            elif sheet_name == 'CapitalInjections':
                cols_map = ['injection_id', 'source_type', 'amount', 'injection_date', 'description', 'created_by', 'created_date']
            elif sheet_name == 'AuditLog':
                cols_map = ['log_id', 'entity_type', 'entity_id', 'action', 'old_value', 'new_value', 'user', 'timestamp']

            batch_data = []
            for row in rows:
                # Handle edge cases where excel col name doesn't exactly match pg col name in AuditLog
                if sheet_name == 'AuditLog' and 'user' not in row and 'User' in row:
                     row['user'] = row['User']
                if sheet_name == 'AuditLog' and 'old_value' not in row and 'OldValue' in row:
                     row['old_value'] = row['OldValue']
                if sheet_name == 'AuditLog' and 'new_value' not in row and 'NewValue' in row:
                     row['new_value'] = row['NewValue']
                
                # Check for alternative property mappings that happened in Excel parser
                
                data_list = []
                for col in cols_map:
                     # try lowercase, uppercase, and titlecase to handle Excel mapping quirks
                     val = row.get(col, row.get(col.upper(), row.get(col.title(), None)))
                     data_list.append(val)
                
                batch_data.append(data_list)
            
            try:
                print(f"Executing bulk insert for {sheet_name} ({len(batch_data)} rows)...")
                pg_db.add_rows(sheet_name, batch_data)
                print(f"Successfully migrated {len(batch_data)} rows for {sheet_name}.")
            except Exception as e:
                print(f"Error inserting rows for {sheet_name}: {e}")

        except Exception as e:
            print(f"Error migrating {sheet_name}: {e}")

    # Migrate System Configs (ID Sequences)
    print("\nMigrating System Configs (ID Sequences)...")
    try:
        config_rows = excel_db.get_all_rows('SystemConfig')
        for row in config_rows:
            key = row.get('config_key', row.get('ConfigKey'))
            val = row.get('config_value', row.get('ConfigValue'))
            desc = row.get('description', row.get('Description'))
            
            if key and val:
                with pg_db.engine.begin() as conn:
                    # UPSERT Logic
                    conn.execute(text('''
                        UPDATE system_config 
                        SET config_value = :v, description = :d, last_updated = :t 
                        WHERE config_key = :k
                    '''), {"k": key, "v": str(val), "d": desc or '', "t": datetime.now()})
        print("System Configs updated.")
    except Exception as e:
        print(f"Error migrating SystemConfig: {e}")

    print("-" * 50)
    print("Migration script completed.")

if __name__ == "__main__":
    migrate_data()
