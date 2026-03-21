from geoalchemy2 import Geometry
from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class POI(Base):
    __tablename__ = "pois"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(200), nullable=False)
    category    = Column(String(100), index=True)
    description = Column(Text, nullable=True)
    address     = Column(String(300), nullable=True)
    geom        = Column(Geometry("POINT", srid=4326))
    created_at  = Column(DateTime, default=datetime.utcnow)


class Trajectory(Base):
    __tablename__ = "trajectories"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(200), nullable=False)
    geom       = Column(Geometry("LINESTRING", srid=4326))
    created_at = Column(DateTime, default=datetime.utcnow)