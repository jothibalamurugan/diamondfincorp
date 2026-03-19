"""
Data Migration Script
Migrates existing Diamond Fincorp data to new optimized schema
"""

import openpyxl
from datetime import datetime
import sys
import os

def migrate_data(source_file, target_file):
    """Migrate data from old structure to new optimized schema"""
    
    print("=" * 60)
    print("DIAMOND FINCORP DATA MIGRATION")
    print("=" * 60)
    
    # Load source workbook
    print(f"\n[1/5] Loading source data from: {source_file}")
    wb_source = openpyxl.load_workbook(source_file, data_only=True)
    
    # Load target workbook
    print(f"[2/5] Loading target database: {target_file}")
    wb_target = openpyxl.load_workbook(target_file)
    
    # ========== MIGRATE CUSTOMERS ==========
    print("\n[3/5] Migrating customers...")
    ws_source_borrowers = wb_source['Borrower_Master ']
    ws_target_customers = wb_target['Customers']
    
    customer_count = 0
    for row in ws_source_borrowers.iter_rows(min_row=2, values_only=True):
        if row[0] is None:  # Skip empty rows
            continue
        
        ws_target_customers.append([
            row[0],  # customer_id (BorrowerID)
            row[1],  # name (BorrowerName)
            row[2],  # phone
            '',      # email (not in source)
            row[3],  # address
            '',      # id_proof_type (not in source)
            '',      # id_proof_number (not in source)
            'ACTIVE' if row[4] == 'Yes' else 'INACTIVE',  # status
            row[5] if row[5] else datetime.now(),  # created_date
            ''       # notes
        ])
        customer_count += 1
    
    print(f"   ✓ Migrated {customer_count} customers")
    
    # ========== MIGRATE LOANS ==========
    print("\n[4/5] Migrating loans...")
    ws_source_loans = wb_source['Loan_Master ']
    ws_target_loans = wb_target['Loans']
    
    loan_count = 0
    for row in ws_source_loans.iter_rows(min_row=2, values_only=True):
        if row[0] is None:  # Skip empty rows
            continue
        
        ws_target_loans.append([
            row[0],  # loan_id (LoanID)
            row[1],  # customer_id (BorrowerID)
            row[3],  # principal_amount
            0,       # add_on_principal
            row[4],  # interest_rate
            row[2] if row[2] else 'DEBT',  # loan_type
            row[5] if row[5] else datetime.now(),  # start_date
            '',      # tenure_months (not in source)
            row[7] if row[7] else 'ACTIVE',  # status
            row[6] if row[6] else '',  # fund_source
            row[8] if row[8] else datetime.now(),  # created_date
            None,    # closed_date (not in source)
            '',      # notes
            row[2] if row[2] else 'DEBT',  # transaction_type
            'subsequent_collection',       # debt_interest_mode
            0,       # pre_deducted_interest
            row[3],  # net_disbursed_amount
            0,       # original_interest_amount
            0,       # waived_interest_amount
            '',      # waiver_reason
            None     # waiver_date
        ])
        loan_count += 1
    
    print(f"   ✓ Migrated {loan_count} loans")
    
    # ========== MIGRATE PAYMENTS ==========
    print("\n[5/5] Migrating payments (this may take a while)...")
    ws_source_payments = wb_source['Payment_Transactions']
    ws_target_payments = wb_target['Payments']
    
    payment_count = 0
    batch_size = 10000
    
    for idx, row in enumerate(ws_source_payments.iter_rows(min_row=2, values_only=True), 1):
        if row[0] is None:  # Skip empty rows
            continue
        
        ws_target_payments.append([
            row[0],  # payment_id (PaymentID)
            row[1],  # loan_id (LoanID)
            row[2],  # customer_id (Borrower)
            row[3] if row[3] else datetime.now(),  # payment_date
            row[4],  # amount (PaymentAmount)
            row[5] if row[5] else 'INTEREST',  # payment_type
            'CASH',  # payment_method (not in source, default to CASH)
            '',      # reference_number (not in source)
            row[7] if row[7] else datetime.now(),  # created_date
            'SYSTEM',  # created_by
            row[6] if row[6] else '',  # notes (Remarks)
            0,       # principal_amount
            row[4] if row[4] else 0,  # interest_amount (safe historical default)
            'None'   # help_category
        ])
        payment_count += 1
        
        # Progress indicator for large datasets
        if payment_count % batch_size == 0:
            print(f"   ... processed {payment_count:,} payments")
    
    print(f"   ✓ Migrated {payment_count:,} payments")
    
    # Update system config with next IDs
    ws_config = wb_target['SystemConfig']
    
    # Find and update next IDs
    for row in ws_config.iter_rows(min_row=2):
        if row[0].value == 'next_customer_id':
            row[1].value = str(customer_count + 1)
        elif row[0].value == 'next_loan_id':
            row[1].value = str(loan_count + 1)
        elif row[0].value == 'next_payment_id':
            row[1].value = str(payment_count + 1)
        elif row[0].value == 'next_help_id':
            row[1].value = '1'
        row[3].value = datetime.now()  # Update last_updated
    
    # Save migrated data
    print(f"\n[SAVING] Writing migrated data to: {target_file}")
    wb_target.save(target_file)
    
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(f"Customers migrated: {customer_count:,}")
    print(f"Loans migrated: {loan_count:,}")
    print(f"Payments migrated: {payment_count:,}")
    print(f"\nNew database file: {target_file}")
    print("You can now use the application with your existing data!")
    print("=" * 60)
    
    return {
        'customers': customer_count,
        'loans': loan_count,
        'payments': payment_count
    }

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    default_source = os.path.normpath(os.path.join(base_dir, '..', 'excel_schema', 'DIAMOND FINCORP DATA .xlsm'))
    default_target = os.path.normpath(os.path.join(base_dir, '..', 'excel_schema', 'LoanManagement_DB.xlsx'))
    source = os.environ.get('LEGACY_EXCEL_SOURCE_PATH', default_source)
    target = os.environ.get('EXCEL_DB_PATH', default_target)
    
    try:
        stats = migrate_data(source, target)
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
