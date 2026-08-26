from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    reports = relationship("Report", back_populates="owner", cascade="all, delete-orphan")


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    risk_level = Column(String, nullable=False)
    confidence = Column(String, nullable=False)

    questionnaire_input = Column(Text, nullable=False)   # JSON string
    portfolio_result = Column(Text, nullable=False)       # JSON string
    shap_result = Column(Text, nullable=True)             # JSON string
    lime_result = Column(Text, nullable=True)             # JSON string

    owner = relationship("User", back_populates="reports")