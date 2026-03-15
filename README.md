# Diamond Fincorp - Professional Loan Management System

## 🎯 Overview

A professional-grade loan management application where:
- **Excel serves as the backend database** (structured, clean data storage)
- **Modern web application serves as the frontend** (professional user interface)
- **Users never touch Excel directly** - all interactions through the application

This is NOT a macro-heavy Excel workbook. This is a proper software application using Excel for data persistence.

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    USER INTERFACE                        │
│              (React Web Application)                     │
│  - Dashboard with analytics                              │
│  - Customer management                                   │
│  - Loan management                                       │
│  - Payment entry with instant summaries                  │
└─────────────────────┬───────────────────────────────────┘
                      │
                      │ REST API
                      ▼
┌─────────────────────────────────────────────────────────┐
│              BUSINESS LOGIC LAYER                        │
│               (FastAPI Backend)                          │
│  - Data validation                                       │
│  - Interest calculations                                 │
│  - Financial analytics                                   │
│  - Transaction management                                │
└─────────────────────┬───────────────────────────────────┘
                      │
                      │ openpyxl
                      ▼
┌─────────────────────────────────────────────────────────┐
│              DATABASE LAYER                              │
│          (Excel Workbook - LoanManagement_DB.xlsx)       │
│  - Customers table                                       │
│  - Loans table                                           │
│  - Payments table                                        │
│  - Interest rate changes                                 │
│  - System configuration                                  │
└─────────────────────────────────────────────────────────┘
```

## ✨ Features

### Customer Management
- Add, edit, search customers
- Track customer status (Active/Inactive)
- Store ID proofs and contact details
- Complete customer history

### Loan Management
- Multiple loans per customer
- Track principal, interest rate, tenure
- Loan lifecycle management (Active/Completed/Defaulted)
- Fund source tracking

### Payment Entry System
**Key Feature**: When you select a customer and loan:
- ✅ Instant loan summary display
- ✅ Outstanding balance calculation
- ✅ Interest accrued calculation
- ✅ Payment history
- ✅ Clear financial status BEFORE entering payment

This ensures you always know the complete picture before recording any transaction.

### Dashboard & Analytics
- Total customers (active vs inactive)
- Total loans (active vs completed)
- Principal outstanding
- Interest collected
- Net profit analysis
- Portfolio health assessment
- Monthly trends

## 🗄️ Database Schema

### Excel Tables

**Customers**
- customer_id (Primary Key)
- name, phone, email, address
- id_proof_type, id_proof_number
- status (ACTIVE/INACTIVE)
- created_date, notes

**Loans**
- loan_id (Primary Key)
- customer_id (Foreign Key)
- principal_amount, interest_rate
- loan_type, start_date, tenure_months
- status (ACTIVE/COMPLETED/DEFAULTED/WRITTEN_OFF)
- fund_source, created_date, closed_date, notes

**Payments**
- payment_id (Primary Key)
- loan_id, customer_id (Foreign Keys)
- payment_date, amount
- payment_type (PRINCIPAL/INTEREST/BOTH)
- payment_method (CASH/CHEQUE/BANK_TRANSFER/UPI)
- reference_number, created_date, created_by, notes

**InterestRateChanges**
- change_id, loan_id
- old_rate, new_rate, effective_date
- reason, created_date, created_by

**LoanEvents**
- event_id, loan_id
- event_type (DISBURSEMENT/RESTRUCTURE/DEFAULT/WAIVER/CLOSURE)
- event_date, amount, description
- created_date, created_by

**FundSources**
- fund_source_id, fund_name
- source_type (OWN_CAPITAL/BANK_LOAN/INVESTOR/OTHER)
- total_amount, interest_cost, status
- created_date, notes

**SystemConfig**
- Configuration parameters
- ID sequence counters
- System settings

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8+
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Step 1: Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Data Migration (If you have existing data)

```bash
cd data_migration
python3 migrate_data.py
```

This will:
- Create the new optimized database structure
- Migrate all your existing customers, loans, and payments
- Preserve all historical data

**Migration Statistics** (from your data):
- ✅ 108 customers migrated
- ✅ 246 loans migrated  
- ✅ 2,650 payments migrated

### Step 3: Start the Backend API

```bash
cd backend
python3 main.py
```

The API will start on: `http://localhost:8000`

You can verify it's running by visiting: `http://localhost:8000` in your browser.

### Step 4: Open the Frontend Application

Simply open the file in your browser:

```bash
cd frontend
# On Mac/Linux:
open index.html

# On Windows:
start index.html

# Or just double-click the file
```

The application will automatically connect to the backend API.

## 📱 Using the Application

### Dashboard
- View portfolio overview
- Monitor key metrics
- Track performance

### Adding a Customer
1. Click "Customers" in sidebar
2. Click "+ Add Customer" button
3. Fill in customer details
4. Click "Create Customer"

### Creating a Loan
1. Click "Loans" in sidebar
2. Click "+ New Loan" button
3. Select customer from dropdown
4. Enter loan details:
   - Principal amount
   - Interest rate (as decimal, e.g., 0.02 = 2% monthly)
   - Loan type
   - Start date
   - Tenure (optional)
5. Click "Create Loan"

### Recording a Payment
1. Click "Payments" in sidebar
2. Select customer from dropdown
3. Select loan from dropdown
4. **Review the loan summary** that appears:
   - Outstanding balance
   - Interest accrued
   - Payment history
5. Enter payment details:
   - Payment date
   - Amount
   - Type (Principal/Interest/Both)
   - Payment method
   - Reference number (for cheque/transfer)
6. Click "Record Payment"

## 💡 Key Design Decisions

### Why Excel as Database?
1. **Familiar**: Business users understand Excel
2. **Portable**: Easy to backup, share, email
3. **Inspectable**: Can open in Excel to verify data (read-only)
4. **No Installation**: No SQL server setup required
5. **Version Control**: Easy to create dated backups

### Why Separate Frontend?
1. **Professional UI**: Modern, responsive interface
2. **Data Validation**: Prevents errors before they reach Excel
3. **Business Logic**: Calculations, validations, workflows
4. **User Experience**: Guided workflows, instant feedback
5. **Security**: Users can't accidentally delete formulas

### Interest Calculation
- Simple interest: `Interest = Principal × Rate × Time`
- Time calculated in months (days / 30)
- Interest accrued continuously from loan start date
- Displayed before every payment for transparency

## 🔧 Configuration

### Changing API Port

Edit `backend/main.py`, last line:
```python
uvicorn.run(app, host="0.0.0.0", port=8000)  # Change 8000 to your port
```

Edit `frontend/index.html`, find:
```javascript
const API_BASE_URL = 'http://localhost:8000';  // Update URL
```

### Excel Database Location

By default: `excel_schema/LoanManagement_DB.xlsx`

To change, set environment variable:
```bash
export EXCEL_DB_PATH=/path/to/your/database.xlsx
python3 backend/main.py
```

## 📈 Business Analytics

The dashboard automatically calculates:

1. **Portfolio Metrics**
   - Total principal disbursed
   - Principal outstanding
   - Collection efficiency

2. **Profitability**
   - Total interest collected = Net Profit
   - Interest accrued (potential income)
   - Interest collected vs accrued gap

3. **Portfolio Health**
   - EXCELLENT: <30% outstanding
   - GOOD: 30-60% outstanding  
   - NEEDS_ATTENTION: >60% outstanding

## 🔒 Data Safety

### Backups
**Critical**: Backup your Excel file regularly!

```bash
# Create dated backup
cp excel_schema/LoanManagement_DB.xlsx \
   excel_schema/backups/LoanManagement_DB_$(date +%Y%m%d).xlsx
```

### Data Integrity
- All operations go through API validation
- Excel formulas not required (calculations in backend)
- Foreign key relationships maintained
- Transaction logging in system

## 🛠️ Troubleshooting

### Backend won't start
```bash
# Check Python version
python3 --version  # Should be 3.8+

# Reinstall dependencies
cd backend
pip install -r requirements.txt --force-reinstall
```

### Frontend can't connect to backend
1. Verify backend is running: `http://localhost:8000`
2. Check browser console for errors (F12)
3. Verify API_BASE_URL in frontend/index.html

### Excel file locked
- Close Excel if you opened the database file
- Only one process can write to Excel at a time
- Backend will wait if file is locked

### Migration issues
```bash
# Verify source file exists
ls -la /path/to/DIAMOND_FINCORP_DATA_.xlsm

# Check file permissions
chmod 644 /path/to/DIAMOND_FINCORP_DATA_.xlsm

# Run migration with verbose output
python3 data_migration/migrate_data.py 2>&1 | tee migration.log
```

## 🎨 Customization

### Adding Custom Fields

1. **Add column to Excel**: Open schema creation script
2. **Update API models**: Edit `backend/main.py` Pydantic models
3. **Update frontend forms**: Edit `frontend/index.html` form fields

### Changing Interest Calculation

Edit `backend/main.py`, function `calculate_interest_accrued()`:
```python
def calculate_interest_accrued(principal, rate, start_date, end_date=None):
    # Modify calculation logic here
    # Current: Simple interest
    # You can implement: Compound, reducing balance, etc.
```

## 📊 API Documentation

Once backend is running, visit:
- Interactive API docs: `http://localhost:8000/docs`
- Alternative UI: `http://localhost:8000/redoc`

### Key Endpoints

**Dashboard**
- `GET /dashboard/stats` - Portfolio statistics
- `GET /dashboard/loan-trends` - Monthly trends

**Customers**
- `GET /customers` - List all customers
- `POST /customers` - Create customer
- `GET /customers/{id}` - Get single customer
- `PUT /customers/{id}` - Update customer

**Loans**
- `GET /loans` - List all loans
- `POST /loans` - Create loan
- `GET /loans/{id}/summary` - Loan summary with calculations
- `PUT /loans/{id}` - Update loan

**Payments**
- `GET /payments` - List all payments
- `POST /payments` - Record payment

## 🚀 Production Deployment

For production use:

1. **Database Backups**: Automated daily backups
2. **User Authentication**: Add login system
3. **Audit Logging**: Track who changed what
4. **Cloud Deployment**: Deploy on AWS/Azure/Heroku
5. **HTTPS**: Secure communication
6. **Multi-user**: Handle concurrent access

## 📞 Support

For issues or questions:
1. Check this README
2. Review API documentation (`/docs`)
3. Check browser console (F12)
4. Review backend logs

## 🎓 Training Guide

### For Data Entry Staff
1. Always start from Dashboard to see overview
2. Navigate using sidebar menu
3. Search customers before adding new ones
4. Always review loan summary before payment entry
5. Double-check amounts before submission

### For Managers
1. Dashboard shows real-time portfolio health
2. Use search to find specific customers/loans
3. Review trends section for business insights
4. Export Excel file for detailed analysis

## 📄 License & Credits

Built for Diamond Fincorp
Professional Loan Management System v1.0.0

---

**Remember**: Excel is your database. The application is your interface. Never edit Excel directly - always use the application!
