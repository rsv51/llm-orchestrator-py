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
    
    # Request information
    name = Column(String(100), index=True)  # Model name requested
    provider_model = Column(String(100))  # Actual provider model used
    provider_name = Column(String(100), index=True)  # Provider name
    status = Column(String(20), index=True)  # success, error
    style = Column(String(50))  # openai, anthropic, gemini
    
    # Error information
    error = Column(Text)  # Error message if status is error
    retry = Column(Integer, default=0)  # Number of retries
    
    # Performance metrics
    proxy_time = Column(Float)  # Total proxy time in seconds
    first_chunk_time = Column(Float)  # Time to first chunk in seconds
    chunk_time = Column(Float)  # Total chunk time in seconds
    tps = Column(Float)  # Tokens per second
    
    # Token usage
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('idx_provider_status', 'provider_name', 'status'),
        Index('idx_created_at', 'created_at'),
        Index('idx_name_status', 'name', 'status'),
    )