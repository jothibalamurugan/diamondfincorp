# Diamond Fincorp Loan Management System - User Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Customer Management](#customer-management)
4. [Loan Management](#loan-management)
5. [Payment Processing](#payment-processing)
6. [Reports & Analytics](#reports--analytics)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Getting Started

### First Time Setup

1. **Extract the application** to a folder on your computer
2. **Run the startup script**:
   - **Windows**: Double-click `start.bat`
   - **Mac/Linux**: Open terminal, navigate to folder, run `./start.sh`

3. **Wait for the server to start** - You'll see:
   ```
   INFO:     Uvicorn running on http://0.0.0.0:8000
   ```

4. **Open the application**:
   - Navigate to the `frontend` folder
   - Double-click `index.html`
   - Your default browser will open the application

### System Requirements
- Python 3.8 or higher
- Modern web browser (Chrome, Firefox, Safari, Edge)
- 100 MB free disk space
- No internet connection required (runs locally)

---

## Dashboard Overview

The Dashboard is your command center - it shows you everything at a glance.

### Key Metrics

**Total Customers**
- Shows total number of customers in system
- Active customer count below

**Total Loans**
- Total number of loans issued
- Currently active loans shown below

**Principal Outstanding**
- How much money is still owed by borrowers
- This is your receivables

**Interest Collected**
- Total interest payments received
- This is your profit!

### Portfolio Summary

**Total Principal Disbursed**
- Sum of all loans ever issued
- Shows your total lending activity

**Principal Collected**
- How much principal has been paid back
- Shows recovery performance

**Net Profit**
- Total interest collected
- Your business profitability

**Portfolio Health**
- **EXCELLENT**: Less than 30% outstanding
- **GOOD**: 30-60% outstanding
- **NEEDS_ATTENTION**: More than 60% outstanding

### How to Use Dashboard

✅ **Start your day here** - Get overview of business
✅ **Check portfolio health** - Monitor overall performance
✅ **Identify trends** - See if collections improving
✅ **Make decisions** - Use data to guide strategy

---

## Customer Management

### Adding a New Customer

1. Click **"Customers"** in the sidebar
2. Click **"+ Add Customer"** button
3. Fill in the form:

   **Required Fields:**
   - Full Name
   - Phone Number

   **Optional but Recommended:**
   - Email
   - Address
   - ID Proof Type (Aadhar, PAN, etc.)
   - ID Proof Number
   - Notes

4. Click **"Create Customer"**

### Finding a Customer

Use the search box at the top of the customer list:
- Search by **customer ID** (e.g., CUST0001)
- Search by **name** (partial match works)
- Search by **phone number**

Results update automatically as you type.

### Customer Status

- **ACTIVE** 🟢 - Can receive new loans
- **INACTIVE** 🔴 - Cannot receive new loans

**When to mark INACTIVE:**
- Customer has settled all loans and left
- Customer has bad payment history
- Legal issues prevent new lending

### Best Practices

✅ **Always search before adding** - Prevent duplicates
✅ **Get complete contact info** - Essential for collections
✅ **Record ID proofs** - Legal requirement and verification
✅ **Add notes** - Record any special information
✅ **Verify phone numbers** - Call to confirm before first loan

---

## Loan Management

### Creating a New Loan

1. Click **"Loans"** in the sidebar
2. Click **"+ New Loan"** button
3. Fill in the loan details:

   **Required Fields:**
   - **Customer**: Select from dropdown
   - **Principal Amount**: Loan amount (e.g., 50000)
   - **Interest Rate**: Monthly rate as decimal (e.g., 0.02 = 2%)
   - **Loan Type**: Personal, Business, Mortgage, or Other
   - **Start Date**: When loan was disbursed

   **Optional Fields:**
   - **Tenure (Months)**: Expected loan duration
   - **Notes**: Any special terms or conditions

4. Click **"Create Loan"**

### Understanding Interest Rates

**IMPORTANT**: Interest rate is entered as a decimal:
- 1% monthly = 0.01
- 2% monthly = 0.02
- 3% monthly = 0.03
- 1.5% monthly = 0.015

**Example Calculation:**
- Loan: ₹100,000
- Rate: 2% monthly (0.02)
- Duration: 3 months
- Interest: ₹100,000 × 0.02 × 3 = ₹6,000

### Loan Types

**Personal**
- Individual consumption loans
- Personal emergencies
- Family expenses

**Business**
- Business capital
- Inventory purchase
- Business expansion

**Mortgage**
- Property-backed loans
- Real estate purchase
- Home renovation

**Other**
- Any other category
- Special arrangements

### Loan Status

- **ACTIVE** 🟢 - Currently active, accepting payments
- **COMPLETED** 🔵 - Fully paid off and closed
- **DEFAULTED** 🔴 - Customer stopped paying
- **WRITTEN_OFF** ⚫ - Irrecoverable, removed from books

### Multiple Loans Per Customer

✅ **Allowed** - Customers can have multiple active loans
✅ **Independent** - Each loan tracked separately
✅ **Separate payments** - Pay one loan at a time

---

## Payment Processing

This is the **most important** section - where money comes in!

### The Smart Payment Entry Process

Our system is designed to give you **complete information** before recording any payment.

### Step-by-Step Payment Entry

**Step 1: Select Customer**
1. Go to **"Payments"** in sidebar
2. Use dropdown to select customer

**Step 2: Select Loan**
- Choose which loan they're paying for
- If customer has multiple loans, each is listed

**Step 3: Review Loan Summary** ⭐ CRITICAL STEP

A **purple panel** appears showing:

📊 **Principal Amount**
- Original loan amount

📊 **Outstanding Balance**
- How much principal is still owed

📊 **Principal Paid**
- How much principal has been paid so far

📊 **Interest Paid**
- How much interest has been paid so far

📊 **Interest Accrued**
- Total interest that has accumulated
- This is what they SHOULD pay

📊 **Days Active**
- How long loan has been running

### Understanding the Numbers

**Example:**
```
Principal Amount:      ₹100,000
Outstanding Balance:   ₹75,000  (still owe)
Principal Paid:        ₹25,000  (already paid)
Interest Paid:         ₹4,000   (already paid)
Interest Accrued:      ₹6,000   (should pay)
Days Active:           90 days
```

**This means:**
- Customer borrowed ₹100,000
- Has paid back ₹25,000 principal
- Still owes ₹75,000 principal
- Has paid ₹4,000 interest
- Should have paid ₹6,000 interest
- Interest pending: ₹2,000

**Step 4: Enter Payment Details**

**Payment Date**
- Date customer made payment
- Can backdate if entering old payments

**Amount**
- How much customer is paying
- Enter actual amount received

**Payment Type**
- **PRINCIPAL**: Paying back the loan amount
- **INTEREST**: Paying the interest charge
- **BOTH**: Mixed payment (less common)

**Payment Method**
- **Cash**: Physical cash
- **Cheque**: Bank cheque
- **Bank Transfer**: NEFT/RTGS/IMPS
- **UPI**: Google Pay, PhonePe, etc.

**Reference Number** (Optional)
- Cheque number
- Transaction ID
- UPI reference

**Notes** (Optional)
- Any additional information
- Payment conditions
- Special circumstances

**Step 5: Record Payment**
- Click **"Record Payment"** button
- Success message appears
- Loan summary updates immediately
- Payment appears in Recent Payments table

### Payment Entry Best Practices

✅ **Always review loan summary first**
- Know what customer owes
- Calculate pending interest
- Verify outstanding balance

✅ **Separate principal and interest**
- Don't mix payment types
- Makes accounting clearer
- Better for reporting

✅ **Record payments same day**
- Don't let them pile up
- Reduces errors
- Better cash flow tracking

✅ **Get payment references**
- Cheque numbers
- Transaction IDs
- Helps with reconciliation

✅ **Add notes for unusual payments**
- Partial payments
- Advance payments
- Settlement amounts

### Common Payment Scenarios

**Scenario 1: Regular Interest Payment**
- Customer pays monthly interest
- Type: INTEREST
- Amount: As per accrued interest

**Scenario 2: Principal Repayment**
- Customer paying back loan amount
- Type: PRINCIPAL
- Amount: Part or full principal

**Scenario 3: Full Settlement**
- Customer closing loan completely
- Enter two separate payments:
  1. All pending interest (Type: INTEREST)
  2. Remaining principal (Type: PRINCIPAL)
- Loan status will show as ready to close

**Scenario 4: Partial Payment**
- Customer can't pay full amount
- Record whatever they pay
- Type based on agreement (usually INTEREST first)
- Note: "Partial payment - will pay rest later"

---

## Reports & Analytics

### Recent Payments Table

Shows last 10 payments for selected loan:
- Payment ID and Date
- Amount paid
- Payment type (color-coded badges)
- Payment method
- Any notes

**Use this to:**
- Verify payment history
- Check last payment date
- Review payment patterns

### Dashboard Trends

**Coming Soon**: Monthly trends showing:
- Disbursements by month
- Collections by month
- Interest income by month

---

## Best Practices

### Daily Operations

**Morning Routine:**
1. Check Dashboard for overview
2. Review any pending actions
3. Prepare for expected payments

**Payment Entry:**
1. Always review loan summary
2. Count cash carefully
3. Record immediately
4. Get customer signature on receipt

**End of Day:**
1. Verify all payments recorded
2. Match cash in hand with records
3. Create daily backup of Excel file

### Weekly Tasks

✅ **Review Portfolio Health**
- Check dashboard metrics
- Identify problem loans
- Plan collection actions

✅ **Backup Database**
- Copy Excel file to safe location
- Name with date (e.g., DB_2025_02_07.xlsx)
- Keep multiple versions

✅ **Follow up on Due Payments**
- Check loans with high accrued interest
- Call customers for pending payments
- Send payment reminders

### Monthly Tasks

✅ **Generate Reports**
- Export Excel file
- Calculate monthly profit
- Review growth trends

✅ **Analyze Performance**
- Collection efficiency
- Default rates
- Interest income

✅ **Plan Strategy**
- Adjust interest rates if needed
- Identify growth opportunities
- Review problem accounts

### Data Entry Rules

**CRITICAL RULES:**
1. ✅ Never edit Excel file directly
2. ✅ Always use the application
3. ✅ Double-check amounts
4. ✅ Never delete payments (make corrections instead)
5. ✅ Keep backup before bulk operations

---

## Troubleshooting

### "Cannot connect to server"

**Solution:**
1. Check if backend is running (terminal window open)
2. Look for "Uvicorn running on http://0.0.0.0:8000"
3. If not running, restart using start script

### "Customer not found in dropdown"

**Solution:**
1. Go to Customers page
2. Use search to verify customer exists
3. Check if customer status is ACTIVE
4. If inactive, cannot create new loans

### "Payment not recorded"

**Solution:**
1. Check browser console (F12)
2. Verify all required fields filled
3. Check amount is positive number
4. Ensure date is valid format

### "Excel file is locked"

**Solution:**
1. Close Excel if you opened the database
2. Only the application should access it
3. Restart backend server
4. Try again

### Numbers seem wrong

**Solution:**
1. Check interest rate (should be decimal)
2. Verify all payments were recorded
3. Check payment types (Principal vs Interest)
4. Review recent payments table

### Slow performance

**Solution:**
1. Close other applications
2. Restart backend server
3. Clear browser cache
4. Check available disk space

---

## Quick Reference Card

### Interest Rate Conversion
| Percentage | Decimal |
|------------|---------|
| 0.5%       | 0.005   |
| 1%         | 0.01    |
| 1.5%       | 0.015   |
| 2%         | 0.02    |
| 2.5%       | 0.025   |
| 3%         | 0.03    |

### Keyboard Shortcuts
- **Tab**: Move to next field
- **Shift+Tab**: Move to previous field
- **Enter**: Submit form (in modals)
- **Esc**: Close modal
- **F5**: Refresh page

### Payment Type Guide
- **PRINCIPAL**: Reducing loan amount
- **INTEREST**: Paying interest charge
- **BOTH**: Use rarely, only when mixed

### Status Colors
- 🟢 Green badge = ACTIVE/COMPLETED
- 🔴 Red badge = INACTIVE/DEFAULTED
- 🔵 Blue badge = INFO/COMPLETED
- 🟡 Yellow badge = WARNING

---

## Support Contacts

**Technical Issues:**
- Check README.md file
- Visit API docs at http://localhost:8000/docs
- Check browser console (F12 key)

**Data Issues:**
- Always backup before trying fixes
- Never edit Excel directly
- Contact system administrator

**Training:**
- Review this user guide
- Practice with test data first
- Ask experienced user for guidance

---

## Remember

✅ **Excel = Database** (Don't edit directly!)  
✅ **Application = Interface** (Use this!)  
✅ **Review before recording** (Check loan summary!)  
✅ **Backup regularly** (Save your data!)  
✅ **Accuracy matters** (Double-check everything!)  

**Your financial data is precious. Handle with care!**

---

*Diamond Fincorp Loan Management System - User Guide v1.0*
