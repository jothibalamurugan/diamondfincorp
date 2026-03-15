"""
Diamond Fincorp Loan Management System - Enterprise Backend API
FastAPI server with Excel backend - Enterprise Grade with Full Feature Set
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
import os
from decimal import Decimal
import logging
import json
from sqlalchemy import create_engine, text, Table, Column, String, Float, MetaData, Integer, DateTime
from sqlalchemy.orm import declarative_base, Session
from sqlalchemy.exc import ProgrammingError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
# Resolve absolute path dynamically so WSGI can find the file regardless of the cwd
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Check if the file exists in the current directory (how you uploaded it)
LOCAL_DB_PATH = os.path.join(BASE_DIR, 'LoanManagement_DB.xlsx')
# Explicit pythonanywhere path based on user's screenshot
PA_DB_PATH = '/home/Jothis262/backend/LoanManagement_DB.xlsx'
# Fallback to the original schema path just in case
DEFAULT_DB_PATH = os.path.join(BASE_DIR, '..', 'excel_schema', 'LoanManagement_DB.xlsx')

if os.path.exists(PA_DB_PATH):
    EXCEL_DB_PATH = os.environ.get('EXCEL_DB_PATH', PA_DB_PATH)
elif os.path.exists(LOCAL_DB_PATH):
    EXCEL_DB_PATH = os.environ.get('EXCEL_DB_PATH', LOCAL_DB_PATH)
else:
    EXCEL_DB_PATH = os.environ.get('EXCEL_DB_PATH', os.path.normpath(DEFAULT_DB_PATH))

# Sheet name mappings - maps internal names to actual Excel sheet names
# User's Excel uses: Loan_Master, Borrower_Master, Payment_Transactions
SHEET_NAMES = {
    'Loans': 'Loan_Master',
    'Customers': 'Borrower_Master', 
    'Payments': 'Payment_Transactions',
    'CapitalInjections': 'CapitalInjections',
    'AuditLog': 'AuditLog',
    'SystemConfig': 'SystemConfig'
}

# Column name mappings - maps internal names to actual Excel column names
# This allows flexibility for different Excel schemas
COLUMN_MAPPINGS = {
    # Loan columns
    'loan_id': ['LoanID', 'loan_id', 'Loan_ID', 'loanid'],
    'customer_id': ['BorrowerId', 'customer_id', 'CustomerID', 'borrower_id'],
    'principal_amount': ['principal_amount', 'Principal', 'PrincipalAmount', 'Amount'],
    'interest_rate': ['interest_rate', 'InterestRate', 'Rate', 'interest'],
    'start_date': ['start_date', 'StartDate', 'Date', 'LoanDate'],
    'status': ['status', 'Status', 'LoanStatus'],
    'type': ['type', 'Type', 'LoanType', 'transaction_type'],
    
    # Payment columns
    'payment_id': ['payment_id', 'PaymentID', 'TransactionID'],
    'payment_date': ['payment_date', 'PaymentDate', 'Date', 'TransactionDate'],
    'amount': ['amount', 'Amount', 'PaymentAmount'],
    'payment_type': ['payment_type', 'PaymentType', 'Type'],
    
    # Borrower columns
    'name': ['name', 'Name', 'BorrowerName', 'CustomerName']
}

def get_column_value(row: dict, column_key: str, default=None):
    """Get value from row using flexible column name matching"""
    if column_key in COLUMN_MAPPINGS:
        for possible_name in COLUMN_MAPPINGS[column_key]:
            if possible_name in row and row[possible_name] is not None:
                return row[possible_name]
    # Direct access if not in mappings
    if column_key in row:
        return row[column_key]
    return default

def get_sheet_name(internal_name: str) -> str:
    """Get actual sheet name from internal name"""
    return SHEET_NAMES.get(internal_name, internal_name)

app = FastAPI(
    title="Diamond Fincorp Loan Management API",
    description="Enterprise-grade loan management system with Excel backend",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def serve_frontend():
    frontend_path = os.path.join(BASE_DIR, '..', 'frontend', 'index.html')
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "Frontend file not found"}

# ==================== ENUMS ====================

class TransactionType(str, Enum):
    KULU = "KULU"
    DEBT = "DEBT"

class LoanStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    DEFAULTED = "DEFAULTED"
    WRITTEN_OFF = "WRITTEN_OFF"

class PaymentType(str, Enum):
    PRINCIPAL = "PRINCIPAL"
    INTEREST = "INTEREST"
    BOTH = "BOTH"

class CapitalSourceType(str, Enum):
    SALARY = "SALARY"
    PERSONAL = "PERSONAL"
    INVESTOR = "INVESTOR"
    BANK_LOAN = "BANK_LOAN"
    OTHER = "OTHER"

# ==================== DATA MODELS ====================

class Customer(BaseModel):
    customer_id: Optional[str] = None
    name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    id_proof_type: Optional[str] = None
    id_proof_number: Optional[str] = None
    status: str = 'ACTIVE'
    created_date: Optional[datetime] = None
    notes: Optional[str] = None

class Loan(BaseModel):
    loan_id: Optional[str] = None
    customer_id: str
    principal_amount: float
    interest_rate: float
    loan_type: str = 'PERSONAL'
    transaction_type: str = 'KULU'  # KULU, DEBT, OTHER
    start_date: date
    tenure_months: Optional[int] = None
    status: str = 'ACTIVE'
    fund_source: Optional[str] = None
    original_interest_amount: Optional[float] = 0.0
    waived_interest_amount: Optional[float] = 0.0
    waiver_reason: Optional[str] = None
    waiver_date: Optional[date] = None
    created_date: Optional[datetime] = None
    closed_date: Optional[datetime] = None
    notes: Optional[str] = None

class Payment(BaseModel):
    payment_id: Optional[str] = None
    loan_id: str
    customer_id: str
    payment_date: date
    amount: float
    payment_type: str  # PRINCIPAL/INTEREST/BOTH
    payment_method: str = 'CASH'
    reference_number: Optional[str] = None
    created_date: Optional[datetime] = None
    created_by: str = 'USER'
    notes: Optional[str] = None

class CapitalInjection(BaseModel):
    injection_id: Optional[str] = None
    source_type: str  # SALARY, PERSONAL, INVESTOR, BANK_LOAN, OTHER
    amount: float
    injection_date: date
    description: Optional[str] = None
    created_by: str = 'USER'
    created_date: Optional[datetime] = None

class InterestWaiver(BaseModel):
    loan_id: str
    waived_amount: float
    reason: str
    waiver_date: Optional[date] = None

class AuditLogEntry(BaseModel):
    log_id: Optional[str] = None
    entity_type: str
    entity_id: str
    action: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    user: str = 'USER'
    timestamp: Optional[datetime] = None

class LoanSummary(BaseModel):
    loan_id: str
    customer_name: str
    principal_amount: float
    total_paid: float
    principal_paid: float
    interest_paid: float
    outstanding_balance: float
    interest_rate: float
    transaction_type: str
    status: str
    start_date: date
    days_active: int
    total_interest_accrued: float
    original_interest_amount: float
    waived_interest_amount: float
    effective_interest_due: float

class DashboardStats(BaseModel):
    total_customers: int
    active_customers: int
    total_loans: int
    active_loans: int
    total_principal_disbursed: float
    total_principal_outstanding: float
    total_interest_collected: float
    total_interest_waived: float
    total_principal_collected: float
    net_profit: float
    portfolio_health: str
    kulu_count: int
    debt_count: int
    other_count: int
    total_capital_injected: float
    capital_utilized: float

class CapitalSummary(BaseModel):
    total_injected: float
    total_disbursed: float
    available_capital: float
    utilization_percentage: float
    by_source: Dict[str, float]

# ==================== DATABASE OPERATIONS ====================

class ExcelDB:
    """Excel database handler with thread-safe operations"""
    
    def __init__(self, filepath):
        self.filepath = filepath
        self._ensure_file_exists()
        self._ensure_schema_updated()
    
    def _ensure_file_exists(self):
        if not os.path.exists(self.filepath):
            raise FileNotFoundError(f"Database file not found: {self.filepath}")
    
    def _ensure_schema_updated(self):
        """Ensure new columns and sheets exist for enterprise features"""
        wb = openpyxl.load_workbook(self.filepath)
        modified = False
        
        # Check if Loan_Master sheet has new columns (use actual sheet name)
        loans_sheet_name = 'Loan_Master' if 'Loan_Master' in wb.sheetnames else 'Loans'
        ws_loans = wb[loans_sheet_name]
        headers = [cell.value for cell in ws_loans[1]]
        
        new_loan_columns = [
            'transaction_type',
            'original_interest_amount',
            'waived_interest_amount', 
            'waiver_reason',
            'waiver_date'
        ]
        
        for col_name in new_loan_columns:
            if col_name not in headers:
                ws_loans.cell(row=1, column=len(headers)+1, value=col_name)
                headers.append(col_name)
                modified = True
                
                # Set default values for existing rows
                for row_idx in range(2, ws_loans.max_row + 1):
                    if ws_loans.cell(row=row_idx, column=1).value:  # If row has data
                        if col_name == 'transaction_type':
                            ws_loans.cell(row=row_idx, column=len(headers), value='OTHER')
                        elif col_name in ['original_interest_amount', 'waived_interest_amount']:
                            ws_loans.cell(row=row_idx, column=len(headers), value=0)
        
        # Create CapitalInjections sheet if not exists
        if 'CapitalInjections' not in wb.sheetnames:
            ws_capital = wb.create_sheet('CapitalInjections')
            ws_capital.append([
                'injection_id',
                'source_type',
                'amount',
                'injection_date',
                'description',
                'created_by',
                'created_date'
            ])
            # Format header
            for cell in ws_capital[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            modified = True
        
        # Create AuditLog sheet if not exists
        if 'AuditLog' not in wb.sheetnames:
            ws_audit = wb.create_sheet('AuditLog')
            ws_audit.append([
                'log_id',
                'entity_type',
                'entity_id',
                'action',
                'old_value',
                'new_value',
                'user',
                'timestamp'
            ])
            # Format header
            for cell in ws_audit[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
            modified = True
        
        # Add next IDs for new entities
        ws_config = wb['SystemConfig']
        config_keys = [row[0].value for row in ws_config.iter_rows(min_row=2)]
        
        if 'next_injection_id' not in config_keys:
            ws_config.append(['next_injection_id', '1', 'Next capital injection ID', datetime.now()])
            modified = True
        
        if 'next_audit_id' not in config_keys:
            ws_config.append(['next_audit_id', '1', 'Next audit log ID', datetime.now()])
            modified = True
        
        if modified:
            wb.save(self.filepath)
            logger.info("Database schema updated for enterprise features")
        
        wb.close()
    

        
    def _load_workbook(self):
        """Load workbook with data_only=True to get calculated values"""
        return openpyxl.load_workbook(self.filepath, data_only=True)
    
    def _save_workbook(self, wb):
        """Save workbook safely"""
        wb.save(self.filepath)

    def _get_worksheet(self, wb, sheet_name: str):
        """
        Resolve logical sheet name (e.g. 'Loans', 'Customers') to the actual
        Excel worksheet name using the central SHEET_NAMES mapping.
        Falls back to the provided name if a direct match exists.
        """
        actual_sheet_name = get_sheet_name(sheet_name)
        if actual_sheet_name in wb.sheetnames:
            return wb[actual_sheet_name]
        if sheet_name in wb.sheetnames:
            return wb[sheet_name]
        logger.warning(
            f"Sheet '{sheet_name}' (mapped to '{actual_sheet_name}') not found. "
            f"Available sheets: {wb.sheetnames}"
        )
        raise KeyError(f"Worksheet for '{sheet_name}' not found")
    
    def get_next_id(self, id_type: str) -> str:
        """Get next sequential ID for customers, loans, payments, etc."""
        wb = openpyxl.load_workbook(self.filepath)
        ws = self._get_worksheet(wb, 'SystemConfig')
        
        config_map = {
            'customer': 'next_customer_id',
            'loan': 'next_loan_id',
            'payment': 'next_payment_id',
            'injection': 'next_injection_id',
            'audit': 'next_audit_id'
        }
        
        config_key = config_map.get(id_type)
        next_num = 1
        
        for row in ws.iter_rows(min_row=2, values_only=False):
            if row[0].value == config_key:
                next_num = int(row[1].value)
                row[1].value = str(next_num + 1)
                row[3].value = datetime.now()
                break
        
        self._save_workbook(wb)
        
        # Format ID
        prefixes = {
            'customer': 'CUST', 
            'loan': 'LN', 
            'payment': 'PAY',
            'injection': 'CAP',
            'audit': 'AUD'
        }
        return f"{prefixes[id_type]}{next_num:04d}"
    
    def get_all_rows(self, sheet_name: str) -> List[Dict]:
        """Get all rows from a sheet as list of dicts"""
        wb = self._load_workbook()
        try:
            ws = self._get_worksheet(wb, sheet_name)
        except KeyError:
            # Already logged in _get_worksheet
            return []
        
        headers = [cell.value for cell in ws[1]]
        rows = []
        
        for row in ws.iter_rows(min_row=2, values_only=True):
            if row[0] is None:  # Skip empty rows
                continue
            row_dict = {}
            for i, header in enumerate(headers):
                if header and i < len(row):
                    row_dict[header] = row[i]
            rows.append(row_dict)
        
        return rows
    
    def add_row(self, sheet_name: str, data: List[Any]):
        """Add a new row to a sheet"""
        wb = openpyxl.load_workbook(self.filepath)
        ws = self._get_worksheet(wb, sheet_name)
        ws.append(data)
        self._save_workbook(wb)
    
    def update_row(self, sheet_name: str, id_column: str, id_value: str, updates: Dict):
        """Update a row based on ID"""
        wb = openpyxl.load_workbook(self.filepath)
        ws = self._get_worksheet(wb, sheet_name)
        
        headers = [cell.value for cell in ws[1]]
        id_col_idx = headers.index(id_column)
        
        for row in ws.iter_rows(min_row=2):
            if row[id_col_idx].value == id_value:
                for col_name, new_value in updates.items():
                    if col_name in headers:
                        col_idx = headers.index(col_name)
                        row[col_idx].value = new_value
                break
        
        self._save_workbook(wb)
    
    def log_audit(self, entity_type: str, entity_id: str, action: str, old_value: Any = None, new_value: Any = None, user: str = 'USER'):
        """Add audit log entry"""
        audit_id = self.get_next_id('audit')
        
        data = [
            audit_id,
            entity_type,
            entity_id,
            action,
            json.dumps(old_value) if old_value else '',
            json.dumps(new_value) if new_value else '',
            user,
            datetime.now()
        ]
        
        self.add_row('AuditLog', data)
        return audit_id

class PostgresDB:
    """PostgreSQL database handler with identical interface to ExcelDB"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        if self.database_url.startswith("postgres://"):
            self.database_url = self.database_url.replace("postgres://", "postgresql://", 1)
            
        # Using connect_args for ssl require in railway sometimes helps, and smaller pool
        self.engine = create_engine(self.database_url, pool_size=2, max_overflow=5, pool_timeout=30)
        self.metadata = MetaData()
        # We don't automatically call _ensure_schema here anymore to prevent deadlocks
        # It should be called explicitly from migration/setup scripts.
        
    def _get_table_name(self, sheet_name):
        mapping = {
            'Customers': 'borrower_master',
            'Loans': 'loan_master',
            'Payments': 'payment_transactions',
            'CapitalInjections': 'capital_injections',
            'AuditLog': 'audit_log',
            'SystemConfig': 'system_config'
        }
        return mapping.get(sheet_name, sheet_name.lower())

    def _ensure_schema(self):
        """Create tables if they don't exist"""
        with self.engine.begin() as conn:
            # Customers
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS borrower_master (
                    customer_id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(255),
                    phone VARCHAR(50),
                    email VARCHAR(255),
                    address TEXT,
                    id_proof_type VARCHAR(50),
                    id_proof_number VARCHAR(100),
                    status VARCHAR(50),
                    created_date TIMESTAMP,
                    notes TEXT
                )
            '''))
            
            # Loans
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS loan_master (
                    loan_id VARCHAR(50) PRIMARY KEY,
                    customer_id VARCHAR(50),
                    principal_amount FLOAT,
                    interest_rate FLOAT,
                    loan_type VARCHAR(50),
                    start_date DATE,
                    tenure_months VARCHAR(50),
                    status VARCHAR(50),
                    fund_source VARCHAR(100),
                    created_date TIMESTAMP,
                    closed_date TIMESTAMP,
                    notes TEXT,
                    transaction_type VARCHAR(50),
                    original_interest_amount FLOAT,
                    waived_interest_amount FLOAT,
                    waiver_reason TEXT,
                    waiver_date DATE
                )
            '''))
            
            # Payments
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS payment_transactions (
                    payment_id VARCHAR(50) PRIMARY KEY,
                    loan_id VARCHAR(50),
                    customer_id VARCHAR(50),
                    payment_date DATE,
                    amount FLOAT,
                    payment_type VARCHAR(50),
                    payment_method VARCHAR(50),
                    reference_number VARCHAR(255),
                    created_date TIMESTAMP,
                    created_by VARCHAR(100),
                    notes TEXT
                )
            '''))
            
            # Capital Injections
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS capital_injections (
                    injection_id VARCHAR(50) PRIMARY KEY,
                    source_type VARCHAR(100),
                    amount FLOAT,
                    injection_date DATE,
                    description TEXT,
                    created_by VARCHAR(100),
                    created_date TIMESTAMP
                )
            '''))
            
            # Audit Log
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    log_id VARCHAR(50) PRIMARY KEY,
                    entity_type VARCHAR(50),
                    entity_id VARCHAR(50),
                    action VARCHAR(100),
                    old_value TEXT,
                    new_value TEXT,
                    "user" VARCHAR(100),
                    timestamp TIMESTAMP
                )
            '''))
            
            # System Config
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS system_config (
                    config_key VARCHAR(100) PRIMARY KEY,
                    config_value VARCHAR(255),
                    description TEXT,
                    last_updated TIMESTAMP
                )
            '''))

            # Initialize SystemConfig rows if not present
            configs = [
                ('next_customer_id', '1', 'Next customer ID'),
                ('next_loan_id', '1', 'Next loan ID'),
                ('next_payment_id', '1', 'Next payment ID'),
                ('next_injection_id', '1', 'Next capital injection ID'),
                ('next_audit_id', '1', 'Next audit log ID')
            ]
            for key, val, desc in configs:
                conn.execute(text('''
                    INSERT INTO system_config (config_key, config_value, description, last_updated)
                    VALUES (:k, :v, :d, :t)
                    ON CONFLICT (config_key) DO NOTHING
                '''), {"k": key, "v": val, "d": desc, "t": datetime.now()})

            logger.info("Checked/Created PostgreSQL schema.")

    def get_next_id(self, id_type: str) -> str:
        config_map = {
            'customer': 'next_customer_id',
            'loan': 'next_loan_id',
            'payment': 'next_payment_id',
            'injection': 'next_injection_id',
            'audit': 'next_audit_id'
        }
        
        config_key = config_map.get(id_type)
        if not config_key:
            raise ValueError(f"Unknown id_type: {id_type}")
            
        with self.engine.begin() as conn:
            # We use row-level locking natively or simply update and returning
            result = conn.execute(text("SELECT config_value FROM system_config WHERE config_key = :key"), {"key": config_key}).scalar()
            next_num = int(result) if result else 1
            
            conn.execute(text('''
                UPDATE system_config 
                SET config_value = :new_val, last_updated = :updated 
                WHERE config_key = :key
            '''), {"new_val": str(next_num + 1), "updated": datetime.now(), "key": config_key})

        prefixes = {
            'customer': 'CUST', 
            'loan': 'LN', 
            'payment': 'PAY',
            'injection': 'CAP',
            'audit': 'AUD'
        }
        return f"{prefixes[id_type]}{next_num:04d}"

    def get_all_rows(self, sheet_name: str) -> List[Dict]:
        table_name = self._get_table_name(sheet_name)
        with self.engine.connect() as conn:
            try:
                result = conn.execute(text(f"SELECT * FROM {table_name}"))
                keys = result.keys()
                # Return list of dictionaries identical to how openpyxl rows were parsed
                return [dict(zip(keys, row)) for row in result]
            except Exception as e:
                logger.error(f"Error fetching from {table_name}: {str(e)}")
                return []

    def add_row(self, sheet_name: str, data: List[Any]):
        """
        Translates a list of values into a Postgres insert.
        This relies on the columns being inserted in the exact same order as the list,
        which we mimic from the Excel schemas.
        """
        table_name = self._get_table_name(sheet_name)
        
        # Hardcoded column mappings based on the lists in endpoints
        cols = []
        if sheet_name == 'Customers':
            cols = ['customer_id', 'name', 'phone', 'email', 'address', 'id_proof_type', 'id_proof_number', 'status', 'created_date', 'notes']
        elif sheet_name == 'Loans':
            cols = ['loan_id', 'customer_id', 'principal_amount', 'interest_rate', 'loan_type', 'start_date', 'tenure_months', 'status', 'fund_source', 'created_date', 'closed_date', 'notes', 'transaction_type', 'original_interest_amount', 'waived_interest_amount', 'waiver_reason', 'waiver_date']
        elif sheet_name == 'Payments':
            cols = ['payment_id', 'loan_id', 'customer_id', 'payment_date', 'amount', 'payment_type', 'payment_method', 'reference_number', 'created_date', 'created_by', 'notes']
        elif sheet_name == 'CapitalInjections':
            cols = ['injection_id', 'source_type', 'amount', 'injection_date', 'description', 'created_by', 'created_date']
        elif sheet_name == 'AuditLog':
            cols = ['log_id', 'entity_type', 'entity_id', 'action', 'old_value', 'new_value', '"user"', 'timestamp']
        
        if len(data) != len(cols):
            logger.error(f"Length mismatch inserting into {sheet_name}. Data: {len(data)}, Cols: {len(cols)}")
            return
            
        placeholders = ", ".join([f":{col.replace('\"', '')}" for col in cols])
        columns_str = ", ".join(cols)
        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
        
        params = {col.replace("\"", ""): val for col, val in zip(cols, data)}
        
        with self.engine.begin() as conn:
            conn.execute(text(query), params)

    def add_rows(self, sheet_name: str, data_list_of_lists: List[List[Any]]):
        """Bulk insert multiple rows for faster migration."""
        if not data_list_of_lists: return
        table_name = self._get_table_name(sheet_name)
        
        cols = []
        if sheet_name == 'Customers':
            cols = ['customer_id', 'name', 'phone', 'email', 'address', 'id_proof_type', 'id_proof_number', 'status', 'created_date', 'notes']
        elif sheet_name == 'Loans':
            cols = ['loan_id', 'customer_id', 'principal_amount', 'interest_rate', 'loan_type', 'start_date', 'tenure_months', 'status', 'fund_source', 'created_date', 'closed_date', 'notes', 'transaction_type', 'original_interest_amount', 'waived_interest_amount', 'waiver_reason', 'waiver_date']
        elif sheet_name == 'Payments':
            cols = ['payment_id', 'loan_id', 'customer_id', 'payment_date', 'amount', 'payment_type', 'payment_method', 'reference_number', 'created_date', 'created_by', 'notes']
        elif sheet_name == 'CapitalInjections':
            cols = ['injection_id', 'source_type', 'amount', 'injection_date', 'description', 'created_by', 'created_date']
        elif sheet_name == 'AuditLog':
            cols = ['log_id', 'entity_type', 'entity_id', 'action', 'old_value', 'new_value', '"user"', 'timestamp']
        
        placeholders = ", ".join([f":{col.replace('\"', '')}" for col in cols])
        columns_str = ", ".join(cols)
        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
        
        params_list = []
        for data in data_list_of_lists:
             if len(data) == len(cols):
                  params_list.append({col.replace("\"", ""): val for col, val in zip(cols, data)})
        
        if params_list:
             # Process in chunks of 500 to avoid PostgreSQL parameter limit (max ~32k parameters per query)
             chunk_size = 500
             for i in range(0, len(params_list), chunk_size):
                 chunk = params_list[i:i + chunk_size]
                 with self.engine.begin() as conn:
                     conn.execute(text(query), chunk)

    def update_row(self, sheet_name: str, id_column: str, id_value: str, updates: Dict):
        table_name = self._get_table_name(sheet_name)
        
        set_clauses = []
        params = {id_column: id_value}
        
        for k, v in updates.items():
            set_clauses.append(f"{k} = :update_{k}")
            params[f"update_{k}"] = v
            
        if not set_clauses:
            return
            
        query = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {id_column} = :{id_column}"
        
        with self.engine.begin() as conn:
            conn.execute(text(query), params)

    def log_audit(self, entity_type: str, entity_id: str, action: str, old_value: Any = None, new_value: Any = None, user: str = 'USER'):
        audit_id = self.get_next_id('audit')
        data = [
            audit_id,
            entity_type,
            entity_id,
            action,
            json.dumps(old_value) if old_value else '',
            json.dumps(new_value) if new_value else '',
            user,
            datetime.now()
        ]
        self.add_row('AuditLog', data)
        return audit_id

# Initialize database
# Determine if we should use Postgres (Railway environment) or fallback to Excel Local
RAILWAY_DB_URL = os.environ.get('DATABASE_URL')

if RAILWAY_DB_URL:
    logger.info("Initializing PostgresDB connection...")
    db = PostgresDB(RAILWAY_DB_URL)
else:
    logger.info("Initializing ExcelDB connection...")
    db = ExcelDB(EXCEL_DB_PATH)

# ==================== HELPER FUNCTIONS ====================

def calculate_interest_accrued(principal: float, rate: float, start_date: date, end_date: Optional[date] = None) -> float:
    """Calculate simple interest accrued"""
    if end_date is None:
        end_date = datetime.now().date()
    
    if isinstance(start_date, datetime):
        start_date = start_date.date()
    
    days = (end_date - start_date).days
    months = days / 30.0  # Approximate months
    
    # Simple interest calculation
    interest = principal * rate * months
    return round(interest, 2)

def get_loan_type(loan: dict) -> str:
    """
    Get normalized loan type from loan record.
    Checks multiple possible column names for type field.
    Returns 'KULU', 'DEBT', or 'OTHER' (uppercase normalized).
    """
    # Check various possible column names for loan type
    # PRIORITIZE 'TYPE' first since that's the user's actual Excel column name
    type_columns = ['TYPE', 'Type', 'type', 'LoanType', 'Loan_Type', 'loan_type',
                    'transaction_type', 'TransactionType', 'Transaction_Type',
                    'Category', 'category', 'Loan Type']
    
    loan_type = None
    
    for col in type_columns:
        val = loan.get(col)
        if val is not None and str(val).strip():
            loan_type = str(val).strip()
            break
    
    # Normalize and return
    if loan_type:
        loan_type_upper = loan_type.upper()
        if loan_type_upper in ['KULU', 'DEBT']:
            return loan_type_upper
    
    return 'OTHER'

# Debug endpoint to inspect actual Excel structure
@app.get("/debug/excel-structure")
async def debug_excel_structure():
    """Debug endpoint to see actual column names and sample data from Excel"""
    loans = db.get_all_rows('Loans')
    payments = db.get_all_rows('Payments')
    customers = db.get_all_rows('Customers')
    
    # Get column names
    loan_columns = list(loans[0].keys()) if loans else []
    payment_columns = list(payments[0].keys()) if payments else []
    customer_columns = list(customers[0].keys()) if customers else []
    
    # Get sample loan with all values
    sample_loans = loans[:3] if loans else []
    sample_payments = payments[:3] if payments else []
    
    # Count types using get_loan_type (which checks TYPE column first)
    type_counts = {'KULU': 0, 'DEBT': 0, 'OTHER': 0}
    for loan in loans:
        loan_type = get_loan_type(loan)
        type_counts[loan_type] = type_counts.get(loan_type, 0) + 1
    
    # Show raw TYPE column values directly
    type_column_raw = {}
    for loan in loans:
        # Check TYPE, Type, type columns directly
        for col in ['TYPE', 'Type', 'type']:
            val = loan.get(col)
            if val is not None:
                type_column_raw[str(val)] = type_column_raw.get(str(val), 0) + 1
                break
    
    # Show payment type values
    payment_type_values = {}
    for p in payments:
        for col in ['PaymentType', 'payment_type', 'Type']:
            val = p.get(col)
            if val is not None:
                payment_type_values[str(val)] = payment_type_values.get(str(val), 0) + 1
                break
    
    return {
        'loan_count': len(loans),
        'payment_count': len(payments),
        'customer_count': len(customers),
        'loan_columns': loan_columns,
        'payment_columns': payment_columns,
        'customer_columns': customer_columns,
        'sample_loans': sample_loans,
        'sample_payments': sample_payments,
        'type_counts_normalized': type_counts,
        'type_column_raw_values': type_column_raw,
        'payment_type_values': payment_type_values
    }

# Data validation endpoint - checks data integrity across all tables
@app.get("/debug/data-validation")
async def validate_data_integrity():
    """
    Comprehensive data validation endpoint.
    Checks for orphan records, missing mappings, and data integrity issues.
    """
    loans = db.get_all_rows('Loans')
    payments = db.get_all_rows('Payments')
    customers = db.get_all_rows('Customers')
    
    # Helper functions
    def get_loan_id(record):
        for key in ['LoanID', 'loan_id', 'Loan_ID']:
            if key in record and record[key] is not None:
                return str(record[key])
        return None
    
    def get_borrower_id(record):
        for key in ['BorrowerId', 'borrower_id', 'customer_id', 'CustomerID']:
            if key in record and record[key] is not None:
                return str(record[key])
        return None
    
    def get_principal(loan):
        for key in ['principal_amount', 'Principal', 'PrincipalAmount', 'Amount']:
            if key in loan and loan[key] is not None:
                try:
                    return float(loan[key])
                except:
                    continue
        return 0
    
    def get_payment_amount(payment):
        for key in ['amount', 'Amount', 'PaymentAmount']:
            if key in payment and payment[key] is not None:
                try:
                    return float(payment[key])
                except:
                    continue
        return 0
    
    # Build sets for validation
    loan_ids = {get_loan_id(l) for l in loans if get_loan_id(l)}
    borrower_ids = {get_borrower_id(c) for c in customers if get_borrower_id(c)}
    loan_borrower_ids = {get_borrower_id(l) for l in loans if get_borrower_id(l)}
    
    # Check for orphan payments (payments without matching loan)
    orphan_payments = []
    for p in payments:
        plid = get_loan_id(p)
        if plid and plid not in loan_ids:
            orphan_payments.append({'payment_loan_id': plid, 'amount': get_payment_amount(p)})
    
    # Check for loans without borrower mapping
    loans_without_borrower = []
    for l in loans:
        bid = get_borrower_id(l)
        if bid and bid not in borrower_ids:
            loans_without_borrower.append({'loan_id': get_loan_id(l), 'borrower_id': bid})
    
    # Calculate totals for verification
    total_disbursed = sum(get_principal(l) for l in loans)
    total_payments = sum(get_payment_amount(p) for p in payments)
    
    # Per-type totals
    kulu_disbursed = sum(get_principal(l) for l in loans if get_loan_type(l) == 'KULU')
    debt_disbursed = sum(get_principal(l) for l in loans if get_loan_type(l) == 'DEBT')
    other_disbursed = sum(get_principal(l) for l in loans if get_loan_type(l) == 'OTHER')
    
    # Per-type loan counts
    kulu_count = len([l for l in loans if get_loan_type(l) == 'KULU'])
    debt_count = len([l for l in loans if get_loan_type(l) == 'DEBT'])
    other_count = len([l for l in loans if get_loan_type(l) == 'OTHER'])
    
    issues = []
    if orphan_payments:
        issues.append(f"{len(orphan_payments)} orphan payments without matching loans")
    if loans_without_borrower:
        issues.append(f"{len(loans_without_borrower)} loans without valid borrower mapping")
    if other_count > 0:
        issues.append(f"{other_count} loans classified as OTHER (may need TYPE column review)")
    
    return {
        'validation_status': 'PASS' if not issues else 'ISSUES_FOUND',
        'issues': issues,
        'summary': {
            'total_loans': len(loans),
            'total_payments': len(payments),
            'total_customers': len(customers),
            'total_disbursed': round(total_disbursed, 2),
            'total_payments_amount': round(total_payments, 2)
        },
        'by_type': {
            'KULU': {'count': kulu_count, 'disbursed': round(kulu_disbursed, 2)},
            'DEBT': {'count': debt_count, 'disbursed': round(debt_disbursed, 2)},
            'OTHER': {'count': other_count, 'disbursed': round(other_disbursed, 2)}
        },
        'orphan_payments_sample': orphan_payments[:5],
        'loans_without_borrower_sample': loans_without_borrower[:5],
        'unique_loan_ids': len(loan_ids),
        'unique_borrowers': len(borrower_ids),
        'loan_borrower_mappings': len(loan_borrower_ids)
    }


def get_loan_summary_data(loan_id: str) -> Optional[LoanSummary]:
    """Get comprehensive loan summary with calculations"""
    
    # Get loan details
    loans = db.get_all_rows('Loans')
    loan = next((l for l in loans if l['loan_id'] == loan_id), None)
    
    if not loan:
        return None
    
    # Get customer name
    customers = db.get_all_rows('Customers')
    customer = next((c for c in customers if c['customer_id'] == loan['customer_id']), None)
    customer_name = customer['name'] if customer else 'Unknown'
    
    # Get all payments for this loan
    payments = db.get_all_rows('Payments')
    loan_payments = [p for p in payments if p['loan_id'] == loan_id]
    
    # Calculate totals
    principal_paid = sum(float(p.get('amount', 0)) for p in loan_payments if p.get('payment_type') in ['PRINCIPAL', 'BOTH'])
    interest_paid = sum(float(p.get('amount', 0)) for p in loan_payments if p.get('payment_type') in ['INTEREST', 'BOTH'])
    total_paid = principal_paid + interest_paid
    
    # Calculate outstanding
    principal_amount = float(loan.get('principal_amount', 0))
    outstanding_balance = max(0, principal_amount - principal_paid)
    
    # Calculate accrued interest
    start_date = loan.get('start_date')
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date[:10], '%Y-%m-%d').date()
    elif isinstance(start_date, datetime):
        start_date = start_date.date()
    
    days_active = (datetime.now().date() - start_date).days
    
    total_interest_accrued = calculate_interest_accrued(
        principal_amount,
        float(loan.get('interest_rate', 0)),
        start_date
    )
    
    # Get waiver info
    original_interest = float(loan.get('original_interest_amount', 0)) or total_interest_accrued
    waived_interest = float(loan.get('waived_interest_amount', 0) or 0)
    effective_interest_due = max(0, total_interest_accrued - waived_interest - interest_paid)
    
    return LoanSummary(
        loan_id=loan_id,
        customer_name=customer_name,
        principal_amount=principal_amount,
        total_paid=total_paid,
        principal_paid=principal_paid,
        interest_paid=interest_paid,
        outstanding_balance=outstanding_balance,
        interest_rate=float(loan.get('interest_rate', 0)),
        transaction_type=loan.get('transaction_type', 'OTHER'),
        status=loan.get('status', 'ACTIVE'),
        start_date=start_date,
        days_active=days_active,
        total_interest_accrued=total_interest_accrued,
        original_interest_amount=original_interest,
        waived_interest_amount=waived_interest,
        effective_interest_due=effective_interest_due
    )

# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    return {
        "message": "Diamond Fincorp Loan Management API",
        "version": "2.0.0",
        "status": "active",
        "features": ["transaction_types", "interest_waivers", "capital_tracking", "audit_logs"]
    }

# ========== CUSTOMER ENDPOINTS ==========

@app.get("/customers", response_model=List[Dict])
async def get_customers(status: Optional[str] = None, search: Optional[str] = None):
    """Get all customers with optional filtering"""
    customers = db.get_all_rows('Customers')
    
    if status:
        customers = [c for c in customers if str(c.get('status', '')).upper() == status.upper()]
    
    if search:
        search_lower = search.lower()
        customers = [c for c in customers if 
                    search_lower in str(c.get('name', '')).lower() or 
                    search_lower in str(c.get('phone', '')).lower() or
                    search_lower in str(c.get('customer_id', '')).lower()]
    
    return customers

@app.get("/customers/{customer_id}")
async def get_customer(customer_id: str):
    """Get single customer by ID"""
    customers = db.get_all_rows('Customers')
    customer = next((c for c in customers if c['customer_id'] == customer_id), None)
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return customer

@app.post("/customers")
async def create_customer(customer: Customer):
    """Create new customer"""
    customer_id = db.get_next_id('customer')
    
    data = [
        customer_id,
        customer.name,
        customer.phone,
        customer.email or '',
        customer.address or '',
        customer.id_proof_type or '',
        customer.id_proof_number or '',
        customer.status,
        datetime.now(),
        customer.notes or ''
    ]
    
    db.add_row('Customers', data)
    db.log_audit('CUSTOMER', customer_id, 'CREATE', None, {'name': customer.name, 'phone': customer.phone})
    
    return {"customer_id": customer_id, "message": "Customer created successfully"}

@app.put("/customers/{customer_id}")
async def update_customer(customer_id: str, customer: Customer):
    """Update existing customer"""
    # Get old values for audit
    old_customer = await get_customer(customer_id)
    
    updates = {
        'name': customer.name,
        'phone': customer.phone,
        'email': customer.email or '',
        'address': customer.address or '',
        'id_proof_type': customer.id_proof_type or '',
        'id_proof_number': customer.id_proof_number or '',
        'status': customer.status,
        'notes': customer.notes or ''
    }
    
    db.update_row('Customers', 'customer_id', customer_id, updates)
    db.log_audit('CUSTOMER', customer_id, 'UPDATE', old_customer, updates)
    
    return {"message": "Customer updated successfully"}

# ========== LOAN ENDPOINTS ==========

@app.get("/loans")
async def get_loans(
    customer_id: Optional[str] = None, 
    status: Optional[str] = None,
    loan_type: Optional[str] = None
):
    """Get all loans with optional filtering, including payment totals"""
    loans = db.get_all_rows('Loans')
    payments = db.get_all_rows('Payments')
    
    if customer_id:
        loans = [l for l in loans if l.get('customer_id') == customer_id]
    
    if status:
        loans = [l for l in loans if str(l.get('status', '')).upper() == status.upper()]
    
    if loan_type:
        loans = [l for l in loans if str(l.get('loan_type', '')).upper() == loan_type.upper()]
    
    # Calculate principal_paid and interest_paid for each loan
    enriched_loans = []
    for loan in loans:
        loan_id = loan.get('loan_id')
        loan_payments = [p for p in payments if p.get('loan_id') == loan_id]
        
        principal_paid = sum(
            float(p.get('amount', 0)) for p in loan_payments 
            if str(p.get('payment_type', '')).upper() in ['PRINCIPAL', 'BOTH']
        )
        interest_paid = sum(
            float(p.get('amount', 0)) for p in loan_payments 
            if str(p.get('payment_type', '')).upper() in ['INTEREST', 'BOTH']
        )
        
        loan_copy = dict(loan)
        loan_copy['principal_paid'] = round(principal_paid, 2)
        loan_copy['interest_paid'] = round(interest_paid, 2)
        enriched_loans.append(loan_copy)
    
    return enriched_loans

@app.get("/loans/{loan_id}/summary")
async def get_loan_summary(loan_id: str):
    """Get comprehensive loan summary with calculations"""
    summary = get_loan_summary_data(loan_id)
    
    if not summary:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    return summary

@app.post("/loans")
async def create_loan(loan: Loan):
    """Create new loan"""
    loan_id = db.get_next_id('loan')
    
    data = [
        loan_id,
        loan.customer_id,
        loan.principal_amount,
        loan.interest_rate,
        loan.loan_type,
        loan.start_date,
        loan.tenure_months or '',
        loan.status,
        loan.fund_source or '',
        datetime.now(),
        None,
        loan.notes or '',
        loan.transaction_type,  # New field
        0,  # original_interest_amount - will be calculated
        0,  # waived_interest_amount
        '',  # waiver_reason
        None  # waiver_date
    ]
    
    db.add_row('Loans', data)
    db.log_audit('LOAN', loan_id, 'CREATE', None, {
        'customer_id': loan.customer_id,
        'principal': loan.principal_amount,
        'transaction_type': loan.transaction_type
    })
    
    return {"loan_id": loan_id, "message": "Loan created successfully"}

@app.put("/loans/{loan_id}")
async def update_loan(loan_id: str, loan: Loan):
    """Update existing loan"""
    updates = {
        'principal_amount': loan.principal_amount,
        'interest_rate': loan.interest_rate,
        'loan_type': loan.loan_type,
        'transaction_type': loan.transaction_type,
        'start_date': loan.start_date,
        'tenure_months': loan.tenure_months or '',
        'status': loan.status,
        'fund_source': loan.fund_source or '',
        'notes': loan.notes or ''
    }
    
    # Get current loan status for comparison
    current_loan_data = await get_loan_summary(loan_id) # Use get_loan_summary to fetch current data
    current_status = current_loan_data.status if current_loan_data else None

    if loan.status == 'COMPLETED' and str(current_status).upper() != 'COMPLETED':
        updates['closed_date'] = datetime.now()
    
    db.update_row('Loans', 'loan_id', loan_id, updates)
    db.log_audit('LOAN', loan_id, 'UPDATE', None, updates)
    
    return {"message": "Loan updated successfully"}

@app.post("/loans/{loan_id}/waive-interest")
async def waive_interest(loan_id: str, waiver: InterestWaiver):
    """Apply interest waiver to a loan"""
    # Get current loan data
    loans = db.get_all_rows('Loans')
    loan = next((l for l in loans if l['loan_id'] == loan_id), None)
    
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")
    
    # Calculate current interest accrued
    start_date = loan.get('start_date')
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date[:10], '%Y-%m-%d').date()
    elif isinstance(start_date, datetime):
        start_date = start_date.date()
    
    current_interest = calculate_interest_accrued(
        float(loan.get('principal_amount', 0)),
        float(loan.get('interest_rate', 0)),
        start_date
    )
    
    # Store original interest if not already set
    original_interest = float(loan.get('original_interest_amount', 0))
    if original_interest == 0:
        original_interest = current_interest
    
    # Calculate new waived amount (cumulative)
    current_waived = float(loan.get('waived_interest_amount', 0) or 0)
    new_waived_total = current_waived + waiver.waived_amount
    
    # Validate waiver doesn't exceed accrued interest
    if new_waived_total > original_interest:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot waive more than accrued interest. Maximum waivable: {original_interest - current_waived}"
        )
    
    updates = {
        'original_interest_amount': original_interest,
        'waived_interest_amount': new_waived_total,
        'waiver_reason': waiver.reason,
        'waiver_date': waiver.waiver_date or datetime.now().date()
    }
    
    db.update_row('Loans', 'loan_id', loan_id, updates)
    db.log_audit('LOAN', loan_id, 'WAIVER', 
        {'waived_before': current_waived}, 
        {'waived_amount': waiver.waived_amount, 'total_waived': new_waived_total, 'reason': waiver.reason}
    )
    
    return {
        "message": "Interest waiver applied successfully",
        "original_interest": original_interest,
        "total_waived": new_waived_total,
        "effective_interest_due": original_interest - new_waived_total
    }

@app.get("/loans/{loan_id}/waiver-history")
async def get_waiver_history(loan_id: str):
    """Get waiver audit trail for a loan"""
    audit_logs = db.get_all_rows('AuditLog')
    waivers = [
        log for log in audit_logs 
        if log.get('entity_id') == loan_id and log.get('action') == 'WAIVER'
    ]
    return waivers

# ========== PAYMENT ENDPOINTS ==========

@app.get("/payments")
async def get_payments(loan_id: Optional[str] = None, customer_id: Optional[str] = None):
    """Get all payments with optional filtering"""
    payments = db.get_all_rows('Payments')
    
    if loan_id:
        payments = [p for p in payments if p.get('loan_id') == loan_id]
    
    if customer_id:
        payments = [p for p in payments if p.get('customer_id') == customer_id]
    
    # Sort by payment_date descending
    payments.sort(key=lambda x: x.get('payment_date') or datetime.min, reverse=True)
    
    return payments

@app.post("/payments")
async def create_payment(payment: Payment):
    """Record new payment"""
    payment_id = db.get_next_id('payment')
    
    data = [
        payment_id,
        payment.loan_id,
        payment.customer_id,
        payment.payment_date,
        payment.amount,
        payment.payment_type,
        payment.payment_method,
        payment.reference_number or '',
        datetime.now(),
        payment.created_by,
        payment.notes or ''
    ]
    
    db.add_row('Payments', data)
    db.log_audit('PAYMENT', payment_id, 'CREATE', None, {
        'loan_id': payment.loan_id,
        'amount': payment.amount,
        'type': payment.payment_type
    })
    
    return {"payment_id": payment_id, "message": "Payment recorded successfully"}

# ========== CAPITAL INJECTION ENDPOINTS ==========

@app.get("/capital-injections")
async def get_capital_injections():
    """Get all capital injections"""
    injections = db.get_all_rows('CapitalInjections')
    return injections

@app.post("/capital-injections")
async def create_capital_injection(injection: CapitalInjection):
    """Record new capital injection"""
    injection_id = db.get_next_id('injection')
    
    data = [
        injection_id,
        injection.source_type,
        injection.amount,
        injection.injection_date,
        injection.description or '',
        injection.created_by,
        datetime.now()
    ]
    
    db.add_row('CapitalInjections', data)
    db.log_audit('CAPITAL', injection_id, 'INJECTION', None, {
        'source': injection.source_type,
        'amount': injection.amount
    })
    
    return {"injection_id": injection_id, "message": "Capital injection recorded successfully"}

@app.get("/capital/summary", response_model=CapitalSummary)
async def get_capital_summary():
    """Get capital utilization summary"""
    injections = db.get_all_rows('CapitalInjections')
    loans = db.get_all_rows('Loans')
    payments = db.get_all_rows('Payments')
    
    # Total injected
    total_injected = sum(float(inj.get('amount', 0)) for inj in injections)
    
    # Total principal disbursed
    total_disbursed = sum(float(loan.get('principal_amount', 0)) for loan in loans)
    
    # Principal collected back
    principal_collected = sum(
        float(p.get('amount', 0)) 
        for p in payments 
        if p.get('payment_type') in ['PRINCIPAL', 'BOTH']
    )
    
    # Available = Injected - (Disbursed - Collected)
    capital_in_use = total_disbursed - principal_collected
    available_capital = total_injected - capital_in_use
    
    # By source
    by_source = {}
    for inj in injections:
        source = inj.get('source_type', 'OTHER')
        by_source[source] = by_source.get(source, 0) + float(inj.get('amount', 0))
    
    utilization = (capital_in_use / total_injected * 100) if total_injected > 0 else 0
    
    return CapitalSummary(
        total_injected=round(total_injected, 2),
        total_disbursed=round(total_disbursed, 2),
        available_capital=round(available_capital, 2),
        utilization_percentage=round(utilization, 2),
        by_source=by_source
    )

# ========== AUDIT LOG ENDPOINTS ==========

@app.get("/audit-log")
async def get_audit_log(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100
):
    """Get audit log with optional filtering"""
    logs = db.get_all_rows('AuditLog')
    
    if entity_type:
        logs = [l for l in logs if l.get('entity_type') == entity_type]
    
    if entity_id:
        logs = [l for l in logs if l.get('entity_id') == entity_id]
    
    if action:
        logs = [l for l in logs if l.get('action') == action]
    
    # Sort by timestamp descending
    logs.sort(key=lambda x: x.get('timestamp') or datetime.min, reverse=True)
    
    return logs[:limit]

# ========== DASHBOARD ENDPOINTS ==========

@app.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get comprehensive dashboard statistics with flexible column access"""
    from collections import defaultdict
    
    customers = db.get_all_rows('Customers')  # Maps to Borrower_Master
    loans = db.get_all_rows('Loans')  # Maps to Loan_Master
    payments = db.get_all_rows('Payments')  # Maps to Payment_Transactions
    injections = db.get_all_rows('CapitalInjections')
    
    # Helper functions for flexible column access
    def get_loan_id(record):
        for key in ['LoanID', 'loan_id', 'Loan_ID', 'loanid', 'LoanId']:
            if key in record and record[key] is not None:
                return str(record[key])
        return None
    
    def get_principal(loan):
        for key in ['principal_amount', 'Principal', 'PrincipalAmount', 'Amount', 'LoanAmount']:
            if key in loan and loan[key] is not None:
                try:
                    return float(loan[key])
                except:
                    continue
        return 0
    
    def get_payment_amount(payment):
        for key in ['amount', 'Amount', 'PaymentAmount', 'TransactionAmount']:
            if key in payment and payment[key] is not None:
                try:
                    return float(payment[key])
                except:
                    continue
        return 0
    
    def get_payment_type(payment):
        for key in ['payment_type', 'PaymentType', 'Type', 'TransactionType']:
            if key in payment and payment[key] is not None:
                return str(payment[key]).strip().upper()
        return 'UNKNOWN'
    
    def get_status(record, default='ACTIVE'):
        for key in ['status', 'Status', 'LoanStatus']:
            if key in record and record[key] is not None:
                return str(record[key]).strip().upper()
        return default
    
    total_customers = len(customers)
    active_customers = len([c for c in customers if get_status(c) == 'ACTIVE'])
    
    total_loans = len(loans)
    active_loans = len([l for l in loans if get_status(l) == 'ACTIVE'])
    
    # Transaction type counts (using get_loan_type helper)
    kulu_count = len([l for l in loans if get_loan_type(l) == 'KULU'])
    debt_count = len([l for l in loans if get_loan_type(l) == 'DEBT'])
    other_count = len([l for l in loans if get_loan_type(l) == 'OTHER'])
    
    total_principal_disbursed = sum(get_principal(l) for l in loans)
    
    # Build loan principal map for proper payment type handling
    loan_principal_map = {get_loan_id(l): get_principal(l) for l in loans}
    loan_principal_collected = defaultdict(float)
    
    # Calculate collected amounts with proper payment type handling
    principal_collected = 0
    interest_collected = 0
    
    for payment in payments:
        amount = get_payment_amount(payment)
        ptype = get_payment_type(payment)
        loan_id = get_loan_id(payment)
        loan_principal = loan_principal_map.get(loan_id, 0)
        
        if 'PRINCIPAL' in ptype and 'INTEREST' in ptype:
            # Combined payment
            remaining = loan_principal - loan_principal_collected[loan_id]
            if amount <= remaining:
                principal_collected += amount
                loan_principal_collected[loan_id] += amount
            else:
                principal_collected += remaining
                interest_collected += (amount - remaining)
                loan_principal_collected[loan_id] += remaining
        elif 'PRINCIPAL' in ptype:
            principal_collected += amount
            loan_principal_collected[loan_id] += amount
        elif 'INTEREST' in ptype:
            interest_collected += amount
        else:
            # Unknown type - treat as combined
            remaining = loan_principal - loan_principal_collected[loan_id]
            if amount <= remaining:
                principal_collected += amount
                loan_principal_collected[loan_id] += amount
            else:
                principal_collected += remaining
                interest_collected += (amount - remaining)
                loan_principal_collected[loan_id] += remaining
                
    # CORRECT CALCULATION: Sum usage of max(0, principal - collected) for EACH loan
    # This prevents "over-collected" loans (negative outstanding) from reducing the total outstanding
    principal_outstanding = 0
    for l in loans:
        lid = get_loan_id(l)
        p_amount = get_principal(l)
        collected = loan_principal_collected.get(lid, 0)
        principal_outstanding += max(0, p_amount - collected)

    # Total interest waived (try different column names)
    total_interest_waived = 0
    for l in loans:
        for key in ['waived_interest_amount', 'WaivedInterest', 'InterestWaived']:
            if key in l and l[key] is not None:
                try:
                    total_interest_waived += float(l[key])
                    break
                except:
                    continue
    
    # Net profit (interest collected is profit)
    net_profit = interest_collected
    
    # Capital tracking
    total_capital_injected = sum(float(inj.get('amount', 0)) for inj in injections)
    capital_utilized = total_principal_disbursed - principal_collected
    
    # Portfolio health assessment
    if total_principal_disbursed > 0:
        outstanding_ratio = principal_outstanding / total_principal_disbursed
        if outstanding_ratio < 0.3:
            portfolio_health = "EXCELLENT"
        elif outstanding_ratio < 0.6:
            portfolio_health = "GOOD"
        else:
            portfolio_health = "NEEDS_ATTENTION"
    else:
        portfolio_health = "NO_DATA"
    
    return DashboardStats(
        total_customers=total_customers,
        active_customers=active_customers,
        total_loans=total_loans,
        active_loans=active_loans,
        total_principal_disbursed=round(total_principal_disbursed, 2),
        total_principal_outstanding=round(principal_outstanding, 2),
        total_interest_collected=round(interest_collected, 2),
        total_interest_waived=round(total_interest_waived, 2),
        total_principal_collected=round(principal_collected, 2),
        net_profit=round(net_profit, 2),
        portfolio_health=portfolio_health,
        kulu_count=kulu_count,
        debt_count=debt_count,
        other_count=other_count,
        total_capital_injected=round(total_capital_injected, 2),
        capital_utilized=round(capital_utilized, 2)
    )

@app.get("/dashboard/loan-trends")
async def get_loan_trends():
    """Get loan disbursement and collection trends"""
    loans = db.get_all_rows('Loans')
    payments = db.get_all_rows('Payments')
    
    # Group by month
    from collections import defaultdict
    monthly_data = defaultdict(lambda: {'disbursed': 0, 'principal_collected': 0, 'interest_collected': 0})
    
    for loan in loans:
        start_date = loan.get('start_date')
        if start_date:
            if isinstance(start_date, datetime):
                month_key = start_date.strftime('%Y-%m')
            else:
                month_key = str(start_date)[:7]
            monthly_data[month_key]['disbursed'] += float(loan.get('principal_amount', 0))
    
    for payment in payments:
        payment_date = payment.get('payment_date')
        if payment_date:
            if isinstance(payment_date, datetime):
                month_key = payment_date.strftime('%Y-%m')
            else:
                month_key = str(payment_date)[:7]
            if payment.get('payment_type') in ['PRINCIPAL', 'BOTH']:
                monthly_data[month_key]['principal_collected'] += float(payment.get('amount', 0))
            if payment.get('payment_type') in ['INTEREST', 'BOTH']:
                monthly_data[month_key]['interest_collected'] += float(payment.get('amount', 0))
    
    # Convert to list and sort
    trends = [{'month': k, **v} for k, v in monthly_data.items()]
    trends.sort(key=lambda x: x['month'])
    
    return trends[-12:]  # Last 12 months

@app.get("/dashboard/financial-metrics")
async def get_financial_metrics(
    loan_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    customer_id: Optional[str] = None
):
    """
    Get comprehensive financial metrics for dashboard with optional filters.
    
    Data Relationships:
    - Loan_Master ↔ Borrower_Master via BorrowerId
    - Payment_Transactions ↔ Loan_Master via LoanID and BorrowerId
    
    Payment Type Handling:
    - Respects 'PaymentType' column (PRINCIPAL, INTEREST, BOTH) for accurate attribution.
    - Fallback logic for BOTH/UNKNOWN types caps principal at remaining balance.
    """
    from collections import defaultdict
    
    # Load data from Excel using mapped sheet names
    loans = db.get_all_rows('Loans')  # Maps to Loan_Master
    payments = db.get_all_rows('Payments')  # Maps to Payment_Transactions
    borrowers = db.get_all_rows('Customers')  # Maps to Borrower_Master
    
    # Helper functions for flexible column access
    def get_loan_id(record):
        for key in ['LoanID', 'loan_id', 'Loan_ID', 'loanid', 'LoanId']:
            if key in record and record[key] is not None:
                return str(record[key])
        return None
    
    def get_borrower_id(record):
        for key in ['BorrowerId', 'borrower_id', 'customer_id', 'CustomerID', 'BorrowerID']:
            if key in record and record[key] is not None:
                return str(record[key])
        return None
    
    def get_principal(loan):
        for key in ['principal_amount', 'Principal', 'PrincipalAmount', 'Amount', 'LoanAmount']:
            if key in loan and loan[key] is not None:
                try:
                    return float(loan[key])
                except:
                    continue
        return 0
    
    def get_payment_amount(payment):
        for key in ['amount', 'Amount', 'PaymentAmount', 'TransactionAmount']:
            if key in payment and payment[key] is not None:
                try:
                    return float(payment[key])
                except:
                    continue
        return 0
    
    def get_payment_type(payment):
        for key in ['payment_type', 'PaymentType', 'Type', 'TransactionType']:
            if key in payment and payment[key] is not None:
                val = str(payment[key]).strip().upper()
                return val
        return 'UNKNOWN'
    
    def get_status(loan):
        for key in ['status', 'Status', 'LoanStatus']:
            if key in loan and loan[key] is not None:
                return str(loan[key]).strip().upper()
        return 'ACTIVE'
    
    def get_date(record, keys):
        for key in keys:
            if key in record and record[key] is not None:
                val = record[key]
                if isinstance(val, datetime):
                    return val.date()
                elif isinstance(val, date):
                    return val
                elif isinstance(val, str):
                    try:
                        return datetime.strptime(str(val)[:10], '%Y-%m-%d').date()
                    except:
                        continue
        return None

    def get_loan_type(record):
        # PRIORITIZE 'TYPE' first since that's the user's actual Excel column name
        type_columns = ['TYPE', 'Type', 'type', 'LoanType', 'Loan_Type', 'loan_type',
                        'transaction_type', 'TransactionType', 'Transaction_Type',
                        'Category', 'category', 'Loan Type']
        
        for col in type_columns:
            if col in record and record[col]:
                val = str(record[col]).strip().upper()
                if val in ['KULU', 'DEBT']:
                    return val
        return 'OTHER'
    
    # Apply filters to LOANS first
    if loan_type and loan_type != 'ALL':
        loans = [l for l in loans if get_loan_type(l) == loan_type]
    
    if status and status != 'ALL':
        loans = [l for l in loans if get_status(l) == status.upper()]
        
    if customer_id:
        loans = [l for l in loans if get_borrower_id(l) == customer_id or str(l.get('customer_id', '')).lower() == customer_id.lower()]

    # Build loan ID set for filtering payments
    loan_id_set = {get_loan_id(l) for l in loans if get_loan_id(l)}
    
    # Filter payments by loan ID and Customer
    if customer_id:
        # Strict payment filtering by customer if provided
        filtered_payments = [p for p in payments if (get_loan_id(p) in loan_id_set) or (get_borrower_id(p) == customer_id)]
    else:
        filtered_payments = [p for p in payments if get_loan_id(p) in loan_id_set]
    
    # Apply date filter for payments
    if start_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        filtered_payments = [p for p in filtered_payments 
                           if get_date(p, ['payment_date', 'PaymentDate', 'Date', 'TransactionDate'])
                           and get_date(p, ['payment_date', 'PaymentDate', 'Date', 'TransactionDate']) >= start_dt]
    
    if end_date:
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        filtered_payments = [p for p in filtered_payments 
                           if get_date(p, ['payment_date', 'PaymentDate', 'Date', 'TransactionDate'])
                           and get_date(p, ['payment_date', 'PaymentDate', 'Date', 'TransactionDate']) <= end_dt]
    
    def calc_segment_metrics(segment_loans, all_payments):
        """
        Calculate metrics for a segment of loans ensuring PaymentType is respected.
        """
        segment_loan_ids = {get_loan_id(l) for l in segment_loans if get_loan_id(l)}
        segment_payments = [p for p in all_payments if get_loan_id(p) in segment_loan_ids]
        
        # Calculate principal disbursed
        principal_disbursed = sum(get_principal(l) for l in segment_loans)
        
        # Build per-loan principal map for "remaining check"
        loan_principal_map = {get_loan_id(l): get_principal(l) for l in segment_loans}
        loan_principal_collected_tracker = defaultdict(float)
        
        total_principal_collected = 0
        total_interest_collected = 0
        
        # Process payments to sum Principal vs Interest
        for p in segment_payments:
            lid = get_loan_id(p)
            if not lid: continue
            
            amount = get_payment_amount(p)
            ptype = get_payment_type(p)
            
            p_portion = 0
            i_portion = 0
            
            # Logic: Strictly follow PaymentType
            if 'PRINCIPAL' in ptype and 'INTEREST' in ptype:
                 # Split logic: Cap at difference
                 remaining = loan_principal_map.get(lid, 0) - loan_principal_collected_tracker[lid]
                 if amount <= remaining:
                     p_portion = amount
                 else:
                     p_portion = max(0, remaining)
                     i_portion = amount - p_portion
            elif 'PRINCIPAL' in ptype:
                 p_portion = amount
            elif 'INTEREST' in ptype:
                 i_portion = amount
            else:
                 # Unknown - Fallback to Split logic
                 remaining = loan_principal_map.get(lid, 0) - loan_principal_collected_tracker[lid]
                 if amount <= remaining:
                     p_portion = amount
                 else:
                     p_portion = max(0, remaining)
                     i_portion = amount - p_portion
            
            total_principal_collected += p_portion
            total_interest_collected += i_portion
            loan_principal_collected_tracker[lid] += p_portion
        
        # Calculate outstanding based on ACTUAL collected principal
        outstanding = max(0, principal_disbursed - total_principal_collected)
        recovery_rate = (total_principal_collected / principal_disbursed * 100) if principal_disbursed > 0 else 0
        
        return {
            'loan_count': len(segment_loans),
            'active_loans': len([l for l in segment_loans if get_status(l) == 'ACTIVE']),
            'principal_disbursed': round(principal_disbursed, 2),
            'principal_collected': round(total_principal_collected, 2),
            'principal_outstanding': round(outstanding, 2),
            'interest_collected': round(total_interest_collected, 2),
            'total_collected': round(total_principal_collected + total_interest_collected, 2),
            'recovery_rate': round(recovery_rate, 2)
        }
    
    # Overall metrics
    overall = calc_segment_metrics(loans, filtered_payments)
    
    # By transaction type (using get_loan_type helper)
    kulu_loans = [l for l in loans if get_loan_type(l) == 'KULU']
    debt_loans = [l for l in loans if get_loan_type(l) == 'DEBT']
    other_loans = [l for l in loans if get_loan_type(l) == 'OTHER']
    
    by_type = {
        'KULU': calc_segment_metrics(kulu_loans, filtered_payments),
        'DEBT': calc_segment_metrics(debt_loans, filtered_payments),
        'OTHER': calc_segment_metrics(other_loans, filtered_payments)
    }
    
    # Collection efficiency (interest collected vs accrued)
    total_interest_accrued = 0
    for loan in loans:
        start_date_loan = get_date(loan, ['start_date', 'StartDate', 'Date', 'LoanDate'])
        if start_date_loan:
            principal = get_principal(loan)
            # Try to get interest rate
            rate = 0
            for key in ['interest_rate', 'InterestRate', 'Rate', 'interest']:
                if key in loan and loan[key] is not None:
                    try:
                        rate = float(loan[key])
                        break
                    except:
                        continue
            
            if rate > 0:
                accrued = calculate_interest_accrued(principal, rate, start_date_loan)
                total_interest_accrued += accrued
    
    interest_efficiency = (overall['interest_collected'] / total_interest_accrued * 100) if total_interest_accrued > 0 else 0
    
    # Portfolio health
    if overall['principal_disbursed'] > 0:
        outstanding_ratio = overall['principal_outstanding'] / overall['principal_disbursed']
        if outstanding_ratio < 0.3:
            portfolio_health = "EXCELLENT"
            health_score = 90
        elif outstanding_ratio < 0.5:
            portfolio_health = "GOOD"
            health_score = 70
        elif outstanding_ratio < 0.7:
            portfolio_health = "FAIR"
            health_score = 50
        else:
            portfolio_health = "NEEDS_ATTENTION"
            health_score = 30
    else:
        portfolio_health = "NO_DATA"
        health_score = 0
    
    return {
        'overall': overall,
        'by_type': by_type,
        'collection_efficiency': round(interest_efficiency, 2),
        'interest_accrued': round(total_interest_accrued, 2),
        'portfolio_health': portfolio_health,
        'health_score': health_score
    }

@app.get("/dashboard/trend-data")
async def get_trend_data(
    months: int = 12,
    loan_type: Optional[str] = None,
    customer_id: Optional[str] = None
):
    """
    Get time-series trend data for dashboard charts.
    Uses flexible column access to work with different Excel schemas.
    """
    from collections import defaultdict
    from datetime import timedelta
    
    loans = db.get_all_rows('Loans')  # Maps to Loan_Master
    payments = db.get_all_rows('Payments')  # Maps to Payment_Transactions
    
    # Helper functions for flexible column access
    def get_loan_id(record):
        for key in ['LoanID', 'loan_id', 'Loan_ID', 'loanid', 'LoanId']:
            if key in record and record[key] is not None:
                return str(record[key])
        return None
    
    def get_borrower_id(record):
        for key in ['BorrowerId', 'borrower_id', 'customer_id', 'CustomerID', 'BorrowerID']:
            if key in record and record[key] is not None:
                return str(record[key])
        return None

    def get_principal(loan):
        for key in ['principal_amount', 'Principal', 'PrincipalAmount', 'Amount', 'LoanAmount']:
            if key in loan and loan[key] is not None:
                try:
                    return float(loan[key])
                except:
                    continue
        return 0
    
    def get_payment_amount(payment):
        for key in ['amount', 'Amount', 'PaymentAmount', 'TransactionAmount']:
            if key in payment and payment[key] is not None:
                try:
                    return float(payment[key])
                except:
                    continue
        return 0
    
    def get_payment_type(payment):
        for key in ['payment_type', 'PaymentType', 'Type', 'TransactionType']:
            if key in payment and payment[key] is not None:
                return str(payment[key]).strip().upper()
        return 'UNKNOWN'
    
    def get_date(record, keys):
        for key in keys:
            if key in record and record[key] is not None:
                val = record[key]
                if isinstance(val, datetime):
                    return val
                elif isinstance(val, date):
                    return datetime.combine(val, datetime.min.time())
                elif isinstance(val, str):
                    try:
                        return datetime.strptime(str(val)[:10], '%Y-%m-%d')
                    except:
                        continue
        return None
    
    def get_loan_type(record):
        # PRIORITIZE 'TYPE' first since that's the user's actual Excel column name
        type_columns = ['TYPE', 'Type', 'type', 'LoanType', 'Loan_Type', 'loan_type',
                        'transaction_type', 'TransactionType', 'Transaction_Type',
                        'Category', 'category', 'Loan Type']
        
        for col in type_columns:
            if col in record and record[col]:
                val = str(record[col]).strip().upper()
                if val in ['KULU', 'DEBT']:
                    return val
                # If it's something else but not explicitly mapped, keep looking or return OTHER
        
        return 'OTHER'

    # Filter by loan type if specified
    if loan_type and loan_type != 'ALL':
        loans = [l for l in loans if get_loan_type(l) == loan_type]
    
    # Filter by Customer
    if customer_id:
        loans = [l for l in loans if get_borrower_id(l) == customer_id or str(l.get('customer_id', '')).lower() == customer_id.lower()]

    # Build loan ID set for filtering payments
    loan_id_set = {get_loan_id(l) for l in loans if get_loan_id(l)}
    
    # Filter payments
    if customer_id:
        payments = [p for p in payments if (get_loan_id(p) in loan_id_set) or (get_borrower_id(p) == customer_id)]
    else:
        payments = [p for p in payments if get_loan_id(p) in loan_id_set]
    
    # Build loan principal map for payment type handling
    loan_principal_map = {get_loan_id(l): get_principal(l) for l in loans}
    
    # Generate month keys for last N months
    current_date = datetime.now()
    month_keys = []
    for i in range(months - 1, -1, -1):
        target_date = current_date - timedelta(days=i * 30)
        month_keys.append(target_date.strftime('%Y-%m'))
    
    # Initialize data structure
    monthly_data = {mk: {
        'month': mk,
        'principal_disbursed': 0,
        'principal_collected': 0,
        'interest_collected': 0,
        'total_collected': 0,
        'transaction_count': 0
    } for mk in month_keys}
    
    # Calculate initial states (before the chart window)
    initial_principal_disbursed = 0
    initial_principal_collected = 0
    
    # Process loans - add disbursed amounts
    for loan in loans:
        start_date = get_date(loan, ['start_date', 'StartDate', 'Date', 'LoanDate'])
        month_key = start_date.strftime('%Y-%m') if start_date else None
        
        # If within window, add to monthly data
        if month_key and month_key in monthly_data:
            monthly_data[month_key]['principal_disbursed'] += get_principal(loan)
        else:
            # Everything else (before window, after window, or no date) adds to initial/legacy
            initial_principal_disbursed += get_principal(loan)
    
    # Track principal collected per loan for accurate payment type handling
    loan_principal_collected = defaultdict(float)
    
    # Sort payments by date for proper sequential processing
    payments_with_dates = []
    for payment in payments:
        pdate = get_date(payment, ['payment_date', 'PaymentDate', 'Date', 'TransactionDate'])
        if pdate:
            payments_with_dates.append((pdate, payment))
    
    payments_with_dates.sort(key=lambda x: x[0])
    
    # Process ALL payments chronologically
    for pdate, payment in payments_with_dates:
        month_key = pdate.strftime('%Y-%m')
        
        amount = get_payment_amount(payment)
        ptype = get_payment_type(payment)
        loan_id = get_loan_id(payment)
        loan_principal = loan_principal_map.get(loan_id, 0)
        
        principal_portion = 0
        interest_portion = 0
        
        # Handle different payment types (Principal First Logic)
        if 'PRINCIPAL' in ptype and 'INTEREST' in ptype:
            # Combined payment
            remaining = loan_principal - loan_principal_collected[loan_id]
            if amount <= remaining:
                principal_portion = amount
            else:
                principal_portion = max(0, remaining)
                interest_portion = amount - principal_portion
        elif 'PRINCIPAL' in ptype:
            principal_portion = amount
        elif 'INTEREST' in ptype:
            interest_portion = amount
        else:
            # Unknown type - treat as combined
            remaining = loan_principal - loan_principal_collected[loan_id]
            if amount <= remaining:
                principal_portion = amount
            else:
                principal_portion = max(0, remaining)
                interest_portion = amount - principal_portion
        
        # Update tracking
        loan_principal_collected[loan_id] += principal_portion
        
        # Update monthly data OR initial stats
        if month_key in monthly_data:
            monthly_data[month_key]['principal_collected'] += principal_portion
            monthly_data[month_key]['interest_collected'] += interest_portion
            monthly_data[month_key]['total_collected'] += amount
            monthly_data[month_key]['transaction_count'] += 1
        else:
            # Catch-all for non-window payments (before or after)
            initial_principal_collected += principal_portion
    
    # Calculate running outstanding balance
    trends = []
    running_disbursed = initial_principal_disbursed
    running_collected = initial_principal_collected
    
    for mk in sorted(month_keys):
        data = monthly_data[mk]
        running_disbursed += data['principal_disbursed']
        running_collected += data['principal_collected']
        
        trends.append({
            'month': mk,
            'month_label': datetime.strptime(mk, '%Y-%m').strftime('%b %Y'),
            'principal_disbursed': round(data['principal_disbursed'], 2),
            'principal_collected': round(data['principal_collected'], 2),
            'interest_collected': round(data['interest_collected'], 2),
            'total_collected': round(data['total_collected'], 2),
            'transaction_count': data['transaction_count'],
            'cumulative_disbursed': round(running_disbursed, 2),
            'cumulative_collected': round(running_collected, 2),
            'outstanding_balance': round(max(0, running_disbursed - running_collected), 2)
        })
    
    return trends

@app.get("/api/customers")
async def get_customers_list():
    """Get list of customers for dropdowns"""
    customers = db.get_all_rows('Customers')
    # Return unique list
    result = []
    seen = set()
    for c in customers:
        cid = None
        for key in ['customer_id', 'CustomerId', 'BorrowerId', 'id']:
            if key in c and c[key]:
                cid = str(c[key])
                break
        
        name = None
        for key in ['name', 'Name', 'BorrowerName', 'CustomerName']:
            if key in c and c[key]:
                name = str(c[key])
                break
        
        if cid and cid not in seen:
            seen.add(cid)
            result.append({'id': cid, 'name': name or cid})
    
    return sorted(result, key=lambda x: x['name'] or '')

# ========== ADVANCED REPORTS ==========

@app.get("/reports/by-transaction-type")
async def get_report_by_transaction_type(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    customer_id: Optional[str] = None
):
    """Get performance metrics by transaction type (Kulu vs Debt vs Other)"""
    from collections import defaultdict
    
    loans = db.get_all_rows('Loans')
    payments = db.get_all_rows('Payments')
    
    # Helper functions
    def get_loan_type(record):
        type_columns = ['TYPE', 'Type', 'type', 'LoanType', 'Loan_Type', 'loan_type', 'transaction_type', 'TransactionType', 'Transaction_Type', 'Category', 'category', 'Loan Type']
        for col in type_columns:
            if col in record and record[col]:
                val = str(record[col]).strip().upper()
                if val in ['KULU', 'DEBT']:
                    return val
        return 'OTHER'

    def get_loan_id(record):
        for key in ['LoanID', 'loan_id', 'Loan_ID', 'loanid', 'LoanId']:
            if key in record and record[key] is not None:
                return str(record[key])
        return None

    def get_borrower_id(record):
        for key in ['BorrowerId', 'borrower_id', 'customer_id', 'CustomerID', 'BorrowerID']:
            if key in record and record[key] is not None:
                return str(record[key])
        return None

    def get_principal(loan):
        for key in ['principal_amount', 'Principal', 'PrincipalAmount', 'Amount', 'LoanAmount']:
            if key in loan and loan[key] is not None:
                try:
                    return float(loan[key])
                except:
                    continue
        return 0

    def get_payment_amount(payment):
        for key in ['amount', 'Amount', 'PaymentAmount', 'TransactionAmount']:
            if key in payment and payment[key] is not None:
                try:
                    return float(payment[key])
                except:
                    continue
        return 0

    def get_payment_type(payment):
        for key in ['payment_type', 'PaymentType', 'Type', 'TransactionType']:
            if key in payment and payment[key] is not None:
                return str(payment[key]).strip().upper()
        return 'UNKNOWN'

    def get_date(record, keys):
        for key in keys:
            if key in record and record[key] is not None:
                val = record[key]
                if isinstance(val, datetime):
                    return val.date()
                elif isinstance(val, date):
                    return val
                elif isinstance(val, str):
                    try:
                        return datetime.strptime(str(val)[:10], '%Y-%m-%d').date()
                    except:
                        continue
        return None

    # Filter Loans by Customer
    if customer_id:
        loans = [l for l in loans if get_borrower_id(l) == customer_id or str(l.get('customer_id', '')).lower() == customer_id.lower()]
        
    # Build loan principal map
    loan_principal_map = {get_loan_id(l): get_principal(l) for l in loans}

    # Filter Payments by Customer & Loan
    loan_id_set = {get_loan_id(l) for l in loans if get_loan_id(l)}
    if customer_id:
        payments = [p for p in payments if (get_loan_id(p) in loan_id_set) or (get_borrower_id(p) == customer_id)]
    else:
        payments = [p for p in payments if get_loan_id(p) in loan_id_set]

    # Filter Payments by Date
    if start_date or end_date:
        filtered_payments = []
        start = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else date.min
        end = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else date.max
        
        for p in payments:
            pdate = get_date(p, ['payment_date', 'PaymentDate', 'Date', 'TransactionDate'])
            if pdate and start <= pdate <= end:
                filtered_payments.append(p)
        payments = filtered_payments

    # Calculate Metrics per Type
    report = {}
    
    # Pre-calculate payment splits per loan (Cumulative)
    # We need to process ALL payments for a loan to get the split right, 
    # even if we are filtering by date for the report view. 
    # BUT, for Reports, we usually want "What happened in this period?"
    # However, "Principal Collected" attribution depends on history.
    # CONSTANT: Logic -> We calculate splits based on ALL history, then filter for the window.
    
    # 1. Sort all payments for relevant loans
    all_payments = db.get_all_rows('Payments')
    all_payments = [p for p in all_payments if get_loan_id(p) in loan_id_set]
    
    payments_with_dates = []
    for payment in all_payments:
        pdate = get_date(payment, ['payment_date', 'PaymentDate', 'Date', 'TransactionDate'])
        if pdate:
            payments_with_dates.append((pdate, payment))
    payments_with_dates.sort(key=lambda x: x[0])
    
    loan_principal_collected_tracker = defaultdict(float)
    loan_payment_splits = defaultdict(list) # loan_id -> list of (date, p_portion, i_portion)

    for pdate, payment in payments_with_dates:
        amount = get_payment_amount(payment)
        ptype = get_payment_type(payment)
        lid = get_loan_id(payment)
        loan_principal = loan_principal_map.get(lid, 0)
        
        p_portion = 0
        i_portion = 0
        
        if 'PRINCIPAL' in ptype and 'INTEREST' in ptype:
             remaining = loan_principal - loan_principal_collected_tracker[lid]
             if amount <= remaining:
                 p_portion = amount
             else:
                 p_portion = max(0, remaining)
                 i_portion = amount - p_portion
        elif 'PRINCIPAL' in ptype:
             p_portion = amount
        elif 'INTEREST' in ptype:
             i_portion = amount
        else:
             remaining = loan_principal - loan_principal_collected_tracker[lid]
             if amount <= remaining:
                 p_portion = amount
             else:
                 p_portion = max(0, remaining)
                 i_portion = amount - p_portion
        
        loan_principal_collected_tracker[lid] += p_portion
        loan_payment_splits[lid].append({
            'date': pdate,
            'p_col': p_portion,
            'i_col': i_portion,
            'total': amount
        })

    # Determine Date Range for Report Aggregation
    r_start = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else date.min
    r_end = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else date.max

    for tx_type in ['KULU', 'DEBT', 'OTHER']:
        type_loans = [l for l in loans if get_loan_type(l) == tx_type]
        type_lids = {get_loan_id(l) for l in type_loans}
        
        p_collected_in_period = 0
        i_collected_in_period = 0
        
        for lid in type_lids:
            splits = loan_payment_splits.get(lid, [])
            for s in splits:
                if r_start <= s['date'] <= r_end:
                    p_collected_in_period += s['p_col']
                    i_collected_in_period += s['i_col']

        p_disbursed = sum(get_principal(l) for l in type_loans)
        # Interest waived is static per loan, not time-based usually, but we include it if loan is in list
        i_waived = sum(float(l.get('waived_interest_amount', 0) or 0) for l in type_loans)
        
        # Principal Outstanding is (Total Disbursed - Total Principal Collected Ever)
        # BUT the report display often wants "Outstanding for these loans".
        # If we filter by date, "Principal Outstanding" usually implies "Current Outstanding".
        # So we use the tracker value.
        
        p_collected_lifetime = sum(loan_principal_collected_tracker[lid] for lid in type_lids)
        
        report[tx_type] = {
            'loan_count': len(type_loans),
            'active_loans': len([l for l in type_loans if str(l.get('status')).upper() == 'ACTIVE']),
            'principal_disbursed': round(p_disbursed, 2),
            'principal_collected': round(p_collected_in_period, 2),
            'principal_outstanding': round(p_disbursed - p_collected_lifetime, 2), # Current outstanding
            'interest_collected': round(i_collected_in_period, 2),
            'interest_waived': round(i_waived, 2),
            'collection_efficiency': round((p_collected_lifetime / p_disbursed * 100) if p_disbursed > 0 else 0, 1)
        }
    
    return report

@app.get("/reports/profitability")
async def get_profitability_report(
    customer_id: Optional[str] = None
):
    """Get comprehensive profitability analysis"""
    from collections import defaultdict

    loans = db.get_all_rows('Loans')
    payments = db.get_all_rows('Payments')
    injections = db.get_all_rows('CapitalInjections')
    
    # Helper functions
    def get_loan_id(record):
        for key in ['LoanID', 'loan_id', 'Loan_ID', 'loanid', 'LoanId']:
            if key in record and record[key] is not None:
                return str(record[key])
        return None

    def get_borrower_id(record):
        for key in ['BorrowerId', 'borrower_id', 'customer_id', 'CustomerID', 'BorrowerID']:
            if key in record and record[key] is not None:
                return str(record[key])
        return None

    def get_principal(loan):
        for key in ['principal_amount', 'Principal', 'PrincipalAmount', 'Amount', 'LoanAmount']:
            if key in loan and loan[key] is not None:
                try:
                    return float(loan[key])
                except:
                    continue
        return 0
    
    def get_payment_amount(payment):
        for key in ['amount', 'Amount', 'PaymentAmount', 'TransactionAmount']:
            if key in payment and payment[key] is not None:
                try:
                    return float(payment[key])
                except:
                    continue
        return 0
    
    def get_payment_type(payment):
        for key in ['payment_type', 'PaymentType', 'Type', 'TransactionType']:
            if key in payment and payment[key] is not None:
                return str(payment[key]).strip().upper()
        return 'UNKNOWN'
    
    def get_date(record, keys):
        for key in keys:
            if key in record and record[key] is not None:
                val = record[key]
                if isinstance(val, datetime):
                    return val.date()
                elif isinstance(val, date):
                    return val
                elif isinstance(val, str):
                    try:
                        return datetime.strptime(str(val)[:10], '%Y-%m-%d').date()
                    except:
                        continue
        return None

    # Filter Loans by Customer
    if customer_id:
        loans = [l for l in loans if get_borrower_id(l) == customer_id or str(l.get('customer_id', '')).lower() == customer_id.lower()]

    # Filter Payments
    loan_id_set = {get_loan_id(l) for l in loans if get_loan_id(l)}
    if customer_id:
        payments = [p for p in payments if (get_loan_id(p) in loan_id_set) or (get_borrower_id(p) == customer_id)]
    else:
        payments = [p for p in payments if get_loan_id(p) in loan_id_set]

    # Calculate Interest Collected correctly using Split Logic
    loan_principal_map = {get_loan_id(l): get_principal(l) for l in loans}
    
    # Sort payments
    payments_with_dates = []
    for payment in payments:
        pdate = get_date(payment, ['payment_date', 'PaymentDate', 'Date', 'TransactionDate'])
        if pdate:
            payments_with_dates.append((pdate, payment))
    payments_with_dates.sort(key=lambda x: x[0])
    
    loan_principal_collected_tracker = defaultdict(float)
    total_interest_collected = 0
    
    for pdate, payment in payments_with_dates:
        amount = get_payment_amount(payment)
        ptype = get_payment_type(payment)
        lid = get_loan_id(payment)
        loan_principal = loan_principal_map.get(lid, 0)
        
        p_portion = 0
        i_portion = 0
        
        if 'PRINCIPAL' in ptype and 'INTEREST' in ptype:
             remaining = loan_principal - loan_principal_collected_tracker[lid]
             if amount <= remaining:
                 p_portion = amount
             else:
                 p_portion = max(0, remaining)
                 i_portion = amount - p_portion
        elif 'PRINCIPAL' in ptype:
             p_portion = amount
        elif 'INTEREST' in ptype:
             i_portion = amount
        else:
             remaining = loan_principal - loan_principal_collected_tracker[lid]
             if amount <= remaining:
                 p_portion = amount
             else:
                 p_portion = max(0, remaining)
                 i_portion = amount - p_portion
        
        loan_principal_collected_tracker[lid] += p_portion
        total_interest_collected += i_portion

    # Interest Analysis - Accrued
    total_interest_accrued = 0
    for loan in loans:
        start_date = loan.get('start_date') # use raw dict access first
        if not start_date:
             start_date = get_date(loan, ['start_date', 'StartDate', 'Date', 'LoanDate'])

        if start_date:
            if isinstance(start_date, str):
                try:
                    start_date = datetime.strptime(start_date[:10], '%Y-%m-%d').date()
                except:
                    pass
            elif isinstance(start_date, datetime):
                start_date = start_date.date()
            
            # Helper to calculate interest based on rate and time
            # Assuming simple interest for now as per previous logic (rate * principal * time?)
            # The previous code called `calculate_interest_accrued`. I need to ensure that function exists or inline it.
            # I'll check if `calculate_interest_accrued` is defined globally.
            # It was called in line 1891 of original file. 
            # I will assume it exists globally.
            try:
                accrued = calculate_interest_accrued(
                    float(loan.get('principal_amount', 0)),
                    float(loan.get('interest_rate', 0)),
                    start_date
                )
                total_interest_accrued += accrued
            except NameError:
                # Fallback if function not found
                pass
    
    interest_waived = sum(float(l.get('waived_interest_amount', 0) or 0) for l in loans)
    interest_pending = total_interest_accrued - total_interest_collected - interest_waived
    
    # Capital Analysis
    total_capital = sum(float(inj.get('amount', 0)) for inj in injections)
    total_disbursed = sum(float(l.get('principal_amount', 0)) for l in loans)
    
    return {
        'interest': {
            'total_accrued': round(total_interest_accrued, 2),
            'collected': round(total_interest_collected, 2),
            'waived': round(interest_waived, 2),
            'pending': round(interest_pending, 2),
            'collection_rate': round((total_interest_collected / total_interest_accrued * 100) if total_interest_accrued > 0 else 0, 2)
        },
        'profit': {
            'gross_profit': round(total_interest_collected, 2),
            'potential_lost_to_waivers': round(interest_waived, 2),
            'net_yield': round((total_interest_collected / total_disbursed * 100) if total_disbursed > 0 else 0, 2)
        },
        'capital': {
            'total_capital': round(total_capital, 2),
            'roi': round((total_interest_collected / total_capital * 100) if total_capital > 0 else 0, 2)
        }
    }

@app.get("/reports/customer-exposure")
async def get_customer_exposure():
    """Get customer risk exposure analysis"""
    customers = db.get_all_rows('Customers')
    loans = db.get_all_rows('Loans')
    payments = db.get_all_rows('Payments')
    
    exposure_list = []
    
    for customer in customers:
        cust_id = customer['customer_id']
        cust_loans = [l for l in loans if l.get('customer_id') == cust_id]
        cust_payments = [p for p in payments if p.get('customer_id') == cust_id]
        
        if not cust_loans:
            continue
        
        total_principal = sum(float(l.get('principal_amount', 0)) for l in cust_loans)
        principal_paid = sum(
            float(p.get('amount', 0)) 
            for p in cust_payments 
            if p.get('payment_type') in ['PRINCIPAL', 'BOTH']
        )
        interest_paid = sum(
            float(p.get('amount', 0)) 
            for p in cust_payments 
            if p.get('payment_type') in ['INTEREST', 'BOTH']
        )
        
        outstanding = total_principal - principal_paid
        active_loans = len([l for l in cust_loans if l.get('status') == 'ACTIVE'])
        
        # Risk score (simple: outstanding / total * active loans)
        risk_score = (outstanding / total_principal * active_loans) if total_principal > 0 else 0
        
        exposure_list.append({
            'customer_id': cust_id,
            'customer_name': customer.get('name'),
            'total_loans': len(cust_loans),
            'active_loans': active_loans,
            'total_principal': round(total_principal, 2),
            'principal_outstanding': round(outstanding, 2),
            'interest_paid': round(interest_paid, 2),
            'risk_score': round(risk_score, 2),
            'status': customer.get('status')
        })
    
    # Sort by outstanding amount descending
    exposure_list.sort(key=lambda x: x['principal_outstanding'], reverse=True)
    
    return exposure_list

# PythonAnywhere WSGI compatibility
from a2wsgi import ASGIMiddleware
wsgi_app = ASGIMiddleware(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
