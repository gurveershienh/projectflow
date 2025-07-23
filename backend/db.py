from models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///project_tracker.db"


engine = create_engine(DATABASE_URL, echo=True)
LocalSession = sessionmaker(engine)

def create_database():
    Base.metadata.create_all(engine)
