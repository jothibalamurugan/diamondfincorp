ALTER TABLE payment_transactions ADD COLUMN is_virtual BOOLEAN DEFAULT FALSE;
ALTER TABLE payment_transactions ADD COLUMN linked_successor_loan_id VARCHAR(20);

UPDATE payment_transactions
SET is_virtual = TRUE
WHERE UPPER(COALESCE(payment_type, '')) = 'BALANCE';

ALTER TABLE loan_master ADD COLUMN parent_loan_id VARCHAR(20) REFERENCES loan_master(loan_id);
ALTER TABLE loan_master ADD COLUMN loan_chain_id VARCHAR(36);
ALTER TABLE loan_master ADD COLUMN fresh_principal DECIMAL(15,2);
ALTER TABLE loan_master ADD COLUMN chain_start_date DATE;

UPDATE loan_master
SET fresh_principal = ROUND(principal_amount - COALESCE(add_on_principal, 0), 2)
WHERE fresh_principal IS NULL;
