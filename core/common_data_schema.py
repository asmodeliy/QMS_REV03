
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean,
    ForeignKey, create_engine, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Product(Base):
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
