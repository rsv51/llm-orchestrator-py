"""
Provider and Model database models.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, Boolean,
    ForeignKey, Index, DateTime
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Provider(Base):
    """Provider configuration model."""
    
    __tablename__ = "providers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)  # openai, anthropic, gemini
    config = Column(Text, nullable=False)  # JSON string: {"api_key": "...", "base_url": "...", "model_mapping": {...}}
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=100, nullable=False)  # Higher priority = tried first
    weight = Column(Integer, default=100, nullable=False)  # Weight for load balancing
    max_retries = Column(Integer, default=3, nullable=False)  # Maximum retry attempts
    timeout = Column(Integer, default=60, nullable=False)  # Request timeout in seconds
    rate_limit = Column(Integer)  # Optional rate limit (requests per minute)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    model_providers = relationship("ModelProvider", back_populates="provider", cascade="all, delete-orphan")
    health_status = relationship("ProviderHealth", back_populates="provider", uselist=False, cascade="all, delete-orphan")
    usage_stats = relationship("ProviderStats", back_populates="provider", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_provider_type_enabled', 'type', 'enabled'),
    )


class ModelConfig(Base):
    """Model configuration model - simplified like llmio-master."""
    
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    remark = Column(String(255))  # Model description
    max_retry = Column(Integer, default=3)  # Maximum retry count
    timeout = Column(Integer, default=30)  # Timeout in seconds
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    model_providers = relationship("ModelProvider", back_populates="model", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_model_name_enabled', 'name', 'enabled'),
    )


class ModelProvider(Base):
    """Model-Provider association with configuration."""
    
    __tablename__ = "model_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    provider_model = Column(String(100), nullable=False)  # Model name at provider
    weight = Column(Integer, default=1)  # Weight for load balancing
    
    # Feature flags
    tool_call = Column(Boolean, default=True)  # Supports tool calling
    structured_output = Column(Boolean, default=True)  # Supports structured output
    image = Column(Boolean, default=False)  # Supports vision/image input
    
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    model = relationship("ModelConfig", back_populates="model_providers")
    provider = relationship("Provider", back_populates="model_providers")
    
    __table_args__ = (
        Index('idx_model_provider', 'model_id', 'provider_id'),
        Index('idx_model_enabled', 'model_id', 'enabled'),
        Index('idx_provider_enabled', 'provider_id', 'enabled'),
    )