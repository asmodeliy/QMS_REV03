"""
Common Product Data Schema
모든 모듈에서 공유하는 제품 기본 정보 데이터베이스 스키마
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean,
    ForeignKey, create_engine, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Product(Base):
    """
    제품 (6310, 5410, 5380, 3300, 3200, 2001, 1003 등)
    """
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True)
    db_name = Column(String(50), unique=True, nullable=False)                       
    product_code = Column(String(100), nullable=True)                        
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
                   
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Product {self.db_name}>"


class ProductVariant(Base):
    """
    제품 변형 (RS, SF 등)
    각 Product는 여러 Tech variant를 가질 수 있음
    """
    __tablename__ = "product_variants"
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    tech = Column(String(50), nullable=False)              
    lane_config = Column(String(100), nullable=False)                         
    process = Column(String(50), nullable=False)                            
    
                         
    ip_name = Column(String(100), nullable=True)                                  
    node = Column(String(50), nullable=True)                      
    ip_address = Column(String(50), nullable=True)                       
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
                   
    product = relationship("Product", back_populates="variants")
    configs = relationship("ProductConfig", back_populates="variant", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ProductVariant {self.product_id}:{self.tech}:{self.lane_config}>"


class ProductConfig(Base):
    """
    제품 구성 정보 (Metal, PDK Version, DRC Version, Calibre 등)
    각 Variant는 여러 Configuration을 가질 수 있음 (예: metal 옵션 여러 개)
    """
    __tablename__ = "product_configs"
    
    id = Column(Integer, primary_key=True)
    variant_id = Column(Integer, ForeignKey("product_variants.id"), nullable=False)
    
                        
    metal_option = Column(String(100), nullable=False)                                                  
    pdk_version = Column(String(50), nullable=False)                              
    
                            
    drc_version = Column(String(50), nullable=True)                          
    calibre_version = Column(String(50), nullable=True)                  
    
                         
    width_um = Column(Float, nullable=True)
    height_um = Column(Float, nullable=True)
    size_um2 = Column(Float, nullable=True)
    
                            
    data_rate_gbps = Column(Float, nullable=True)                        
    power_mw = Column(Float, nullable=True)                          
    
                       
    version = Column(String(50), nullable=True)                              
    customer = Column(String(100), nullable=True)                                  
    delivery_date = Column(String(50), nullable=True)                
    
              
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
                   
    variant = relationship("ProductVariant", back_populates="configs")
    
    def __repr__(self):
        return f"<ProductConfig {self.variant_id}:{self.metal_option}>"


class CommonDataLog(Base):
    """
    공통 데이터 변경 로그
    """
    __tablename__ = "common_data_logs"
    
    id = Column(Integer, primary_key=True)
    action = Column(String(50), nullable=False)                                
    table_name = Column(String(100), nullable=False)                                       
    record_id = Column(Integer, nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    user = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<CommonDataLog {self.action}:{self.table_name}:{self.record_id}>"
