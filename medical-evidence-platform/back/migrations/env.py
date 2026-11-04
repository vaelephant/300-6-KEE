import os
from alembic import context
from sqlalchemy import create_engine
from app.models import metadata
url=os.environ.get('DATABASE_URL','sqlite:///development.db')
if context.is_offline_mode():
    context.configure(url=url,target_metadata=metadata,literal_binds=True)
    with context.begin_transaction():context.run_migrations()
else:
    engine=create_engine(url)
    with engine.connect() as connection:
        if engine.dialect.name=='sqlite':connection.exec_driver_sql('PRAGMA foreign_keys=ON');connection.commit()
        context.configure(connection=connection,target_metadata=metadata)
        with context.begin_transaction():context.run_migrations()
