from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from .session import Base


class Claim(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    claim_id = Column(String, unique=True, index=True, nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    verifications = relationship("Verification", back_populates="claim")
    evidence_items = relationship("Evidence", back_populates="claim")
    reviews = relationship("Review", back_populates="claim")


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    claim_id_fk = Column(Integer, ForeignKey("claims.id"), nullable=False)
    source = Column(String, nullable=False)
    url = Column(Text, nullable=True)
    title = Column(Text, nullable=True)
    snippet = Column(Text, nullable=False)
    published_at = Column(DateTime, nullable=True)
    source_credibility = Column(Integer, nullable=True)

    claim = relationship("Claim", back_populates="evidence_items")


class Verification(Base):
    __tablename__ = "verifications"

    id = Column(Integer, primary_key=True, index=True)
    claim_id_fk = Column(Integer, ForeignKey("claims.id"), nullable=False)
    task_id = Column(String, index=True, nullable=False)
    ai_verdict = Column(String, nullable=False)
    ai_score = Column(Integer, nullable=False)
    ai_confidence = Column(Integer, nullable=False)
    raw_result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Reviewer override
    overridden = Column(Boolean, default=False, nullable=False)
    final_verdict = Column(String, nullable=True)

    claim = relationship("Claim", back_populates="verifications")
    reviews = relationship("Review", back_populates="verification")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    claim_id_fk = Column(Integer, ForeignKey("claims.id"), nullable=False)
    verification_id_fk = Column(Integer, ForeignKey("verifications.id"), nullable=False)
    reviewer = Column(String, nullable=True)
    decision = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    claim = relationship("Claim", back_populates="reviews")
    verification = relationship("Verification", back_populates="reviews")
