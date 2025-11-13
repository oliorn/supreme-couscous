from sqlalchemy import Column, Integer, String
from .database import Base

class Company(Base):
    __tablename__ = "Companies"  # taflan í google cloud

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    url = Column(String)
    description = Column(String)
