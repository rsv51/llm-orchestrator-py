"""
Request log database model.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Index

from app.core.database import Base


class RequestLog(Base):
    """Request log model for tracking API requests."""
    
    __tablename__ = "request_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, index=True)  # Provider ID (FK not enforced for flexibility)
    
    # Request information
    model = Column(String(100), index=True)  # Model name requested
    endpoint = Column(String(255))  # API endpoint
    method = Column(String(10))  # HTTP method
    status_code = Column(Integer, index=True)  # HTTP status code
    
    # Error information
    error_message = Column(Text)  # Error message if failed
    
    # Performance metrics
    latency_ms = Column(Integer)  # Total latency in milliseconds
    
    # Token usage
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost = Column(Float)  # Estimated cost
    
    # User information
    user_id = Column(String(100), index=True)  # User identifier
    ip_address = Column(String(50))  # Client IP address
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_provider_status', 'provider_name', 'status'),
        Index('idx_created_at', 'created_at'),
        Index('idx_name_status', 'name', 'status'),
    )