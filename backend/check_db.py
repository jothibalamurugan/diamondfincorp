import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    tables = ['customers', 'loans', 'payments', 'help', 'capital_injections', 'audit_log', 'system_config']
    for table in tables:
        res = conn.execute(text(f'SELECT count(*) FROM {table}'))
        print(f'{table}: {res.scalar()}')
