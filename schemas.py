"""
Database Schemas for Marketplace

Each Pydantic model represents a collection in MongoDB. The collection name is the lowercase of the class name.

Collections:
- user
- shop
- product
- order
- cart
- review
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class User(BaseModel):
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    avatar: Optional[str] = Field(None, description="Avatar image URL")
    is_vendor: bool = Field(False, description="Whether user can sell")
    bio: Optional[str] = Field(None, description="Short bio for profile/shop")


class Shop(BaseModel):
    vendor_id: str = Field(..., description="Owner user id")
    name: str = Field(..., description="Shop name")
    description: Optional[str] = Field(None, description="Shop description")
    banner: Optional[str] = Field(None, description="Banner image URL")
    logo: Optional[str] = Field(None, description="Logo image URL")


class Product(BaseModel):
    shop_id: str = Field(..., description="Shop id this product belongs to")
    vendor_id: str = Field(..., description="Vendor user id")
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in USD")
    category: Optional[str] = Field(None, description="Product category")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    stock: int = Field(0, ge=0, description="Units in stock")
    tags: List[str] = Field(default_factory=list, description="Search tags")


class Cart(BaseModel):
    user_id: str = Field(..., description="User id owning the cart")
    items: List[dict] = Field(default_factory=list, description="List of {product_id, qty}")


class Order(BaseModel):
    user_id: str = Field(..., description="User who placed the order")
    items: List[dict] = Field(..., description="List of {product_id, qty, price}")
    total: float = Field(..., ge=0, description="Total amount")
    status: str = Field("paid", description="Order status")
    payment_ref: Optional[str] = Field(None, description="Reference to payment")


class Review(BaseModel):
    product_id: str = Field(...)
    user_id: str = Field(...)
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
