from database.connection import get_sync_engine
from sqlalchemy import inspect
engine = get_sync_engine()
inspector = inspect(engine)
for table_name in inspector.get_table_names():
    print(f"Table: {table_name}")
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    print(f"  Columns: {columns}")
