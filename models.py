import os
from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, Index
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')

# Create an engine and reflect the database schema
DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)
Base = declarative_base()

class Mtgs(Base):
    __tablename__ = "mtgs"
    mtgsid = Column(BigInteger, primary_key=True, autoincrement=True)
    meetCode = Column(String(25), unique=True, index=True)
    date = Column(String(15))
    venueAbbr = Column(String(15))
    meetUrl = Column(String(255))
    races = relationship("Races", back_populates="mtg",order_by="Races.raceNum")

class Races(Base):
    __tablename__ = "races"
    racesid = Column(BigInteger, primary_key=True, autoincrement=True)
    meetCode = Column(String(25), ForeignKey("mtgs.meetCode", ondelete="CASCADE"), index=True)
    raceNum = Column(Integer)
    distance = Column(String(15))

    # Relationship with Mtgs
    mtg = relationship("Mtgs", back_populates="races")

    # Relationship with Fields
    fields = relationship("Fields", back_populates="race")

    # Relationship with Horses via Fields
    horses = relationship(
        "Horses",
        secondary="fields",
        primaryjoin="Races.racesid == Fields.racesid",
        secondaryjoin="Fields.horseid == Horses.horseid",
        viewonly=True,
    )

class Fields(Base):
    __tablename__ = "fields"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    racesid = Column(BigInteger, ForeignKey("races.racesid", ondelete="CASCADE"), index=True)
    horseid = Column(BigInteger, ForeignKey("horses.horseid", ondelete="CASCADE"), index=True)

    # Relationships
    race = relationship("Races", back_populates="fields")
    horse = relationship("Horses", back_populates="fields")

class Horses(Base):
    __tablename__ = "horses"
    horseid = Column(BigInteger, primary_key=True, autoincrement=True)
    horsename = Column(String(255))

    # Relationship with Fields
    fields = relationship("Fields", back_populates="horse")

async def init_db():
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
