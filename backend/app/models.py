"""ORM models for queries. They mirror schema.sql and never create tables."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Ship(Base):
    __tablename__ = "ships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(Text, unique=True)


class Booking(Base):
    __tablename__ = "bookings"

    # id, status and created_at are filled in by the database.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ship_id: Mapped[int] = mapped_column(Integer, ForeignKey("ships.id"))
    pilot_name: Mapped[str] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
