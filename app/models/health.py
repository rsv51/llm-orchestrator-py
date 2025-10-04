"""
Provider health and statistics database models.
"""
from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    ForeignKey, DateTime, Date, Index
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ProviderHealth(Base):
    """Provider health status tracking."""
    
    __tablename__ = "provider_health"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), unique=True, nullable=False)
    
    is_healthy = Column(Boolean, default=True, index=True)
    error_count = Column(Integer, default=0)
    last_error = Column(Text)
    last_status_code = Column(Integer)
    last_validated_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_success_at = Column(DateTime)
    next_retry_at = Column(DateTime, index=True)
    consecutive_successes = Column(Integer, default=0)
    
    # Relationships
    provider = relationship("Provider", back_populates="health_status")
    
    __table_args__ = (
        Index('idx_health_provider_status', 'provider_id', 'is_healthy'),
    )


class ProviderStats(Base):
    """Provider usage statistics by date."""
    
    __tablename__ = "provider_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    
    total_requests = Column(Integer, default=0)
    success_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    
    total_tokens = Column(Integer, default=0)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    
    avg_response_time = Column(Float, default=0.0)
    last_used_at = Column(DateTime, index=True)
    
    # Relationships
    provider = relationship("Provider", back_populates="usage_stats")
    
    __table_args__ = (
        Index('idx_provider_date', 'provider_id', 'date', unique=True),
    )


class HealthCheckConfig(Base):
    """Health check configuration (singleton table)."""
    
    __tablename__ = "health_check_config"
    
    id = Column(Integer, primary_key=True)
    enabled = Column(Boolean, default=True)
    interval_minutes = Column(Integer, default=5)
    max_error_count = Column(Integer, default=5)
    retry_after_hours = Column(Integer, default=1)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)