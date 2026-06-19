import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from server.database import Base
from server.models import Customer, License, ActivationLog, AdminUser

def test_database_models():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    
    # Inspect tables to check they exist
    inspector = inspect(engine)
    assert inspector.has_table("customers")
    assert inspector.has_table("licenses")
    assert inspector.has_table("activation_logs")
    assert inspector.has_table("admin_users")
