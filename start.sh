#!/bin/bash

# Diamond Fincorp Loan Management System - Quick Start Script

echo "============================================================"
echo "     DIAMOND FINCORP LOAN MANAGEMENT SYSTEM"
echo "                 Quick Start Script"
echo "============================================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check Python installation
echo -e "${BLUE}[1/5]${NC} Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗${NC} Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓${NC} Python ${PYTHON_VERSION} found"

# Install dependencies
echo ""
echo -e "${BLUE}[2/5]${NC} Installing Python dependencies..."
cd backend
pip install -r requirements.txt --quiet --disable-pip-version-check
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Dependencies installed successfully"
else
    echo -e "${RED}✗${NC} Failed to install dependencies"
    exit 1
fi
cd ..

# Check if database exists
echo ""
echo -e "${BLUE}[3/5]${NC} Checking database..."
if [ -f "excel_schema/LoanManagement_DB.xlsx" ]; then
    echo -e "${GREEN}✓${NC} Database found: excel_schema/LoanManagement_DB.xlsx"
    
    # Check if it has data
    CUSTOMER_COUNT=$(python3 -c "
import openpyxl
wb = openpyxl.load_workbook('excel_schema/LoanManagement_DB.xlsx', data_only=True)
ws = wb['Customers']
print(ws.max_row - 1)
" 2>/dev/null)
    
    if [ "$CUSTOMER_COUNT" -gt 0 ]; then
        echo -e "${GREEN}✓${NC} Database contains ${CUSTOMER_COUNT} customers"
    else
        echo -e "${YELLOW}!${NC} Database is empty (no customers yet)"
    fi
else
    echo -e "${YELLOW}!${NC} Database not found. Creating new database..."
    cd excel_schema
    python3 create_database.py
    cd ..
fi

# Create output directory for reports/exports
echo ""
echo -e "${BLUE}[4/5]${NC} Setting up directories..."
mkdir -p excel_schema/backups
mkdir -p logs
echo -e "${GREEN}✓${NC} Directories created"

# Start the backend server
echo ""
echo -e "${BLUE}[5/5]${NC} Starting backend server..."
echo ""
echo "============================================================"
echo -e "${GREEN}STARTING APPLICATION${NC}"
echo "============================================================"
echo ""
echo -e "Backend API will start on: ${BLUE}http://localhost:8000${NC}"
echo -e "API Documentation: ${BLUE}http://localhost:8000/docs${NC}"
echo ""
echo -e "To open the frontend, open this file in your browser:"
echo -e "${YELLOW}frontend/index.html${NC}"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "============================================================"
echo ""

# Set environment variable for Excel DB path
export EXCEL_DB_PATH="$(pwd)/excel_schema/LoanManagement_DB.xlsx"

# Start the server
cd backend
python3 main.py
