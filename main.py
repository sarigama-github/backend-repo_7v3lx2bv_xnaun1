import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import User, Shop, Product, Cart, Order, Review

app = FastAPI(title="Marketplace API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helpers
class IdModel(BaseModel):
    id: str


def to_obj_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")


def serialize(doc: dict):
    if not doc:
        return doc
    doc["id"] = str(doc.pop("_id"))
    return doc


@app.get("/")
def read_root():
    return {"message": "Marketplace API running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:20]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# Users
@app.post("/api/users", response_model=dict)
def create_user(user: User):
    user_id = create_document("user", user)
    return {"id": user_id}


@app.get("/api/users", response_model=List[dict])
def list_users(limit: Optional[int] = 50):
    docs = get_documents("user", {}, limit)
    return [serialize(d) for d in docs]


# Shops
@app.post("/api/shops", response_model=dict)
def create_shop(shop: Shop):
    shop_id = create_document("shop", shop)
    return {"id": shop_id}


@app.get("/api/shops", response_model=List[dict])
def list_shops(vendor_id: Optional[str] = None, limit: Optional[int] = 50):
    query = {"vendor_id": vendor_id} if vendor_id else {}
    docs = get_documents("shop", query, limit)
    return [serialize(d) for d in docs]


@app.get("/api/shops/{shop_id}", response_model=dict)
def get_shop(shop_id: str):
    doc = db["shop"].find_one({"_id": to_obj_id(shop_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Shop not found")
    return serialize(doc)


# Products
@app.post("/api/products", response_model=dict)
def create_product(product: Product):
    prod_id = create_document("product", product)
    return {"id": prod_id}


@app.get("/api/products", response_model=List[dict])
def list_products(shop_id: Optional[str] = None, q: Optional[str] = None, category: Optional[str] = None, limit: Optional[int] = 50):
    query = {}
    if shop_id:
        query["shop_id"] = shop_id
    if category:
        query["category"] = category
    if q:
        # Simple search across title and tags
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"tags": {"$elemMatch": {"$regex": q, "$options": "i"}}}
        ]
    docs = get_documents("product", query, limit)
    return [serialize(d) for d in docs]


@app.get("/api/products/{product_id}", response_model=dict)
def get_product(product_id: str):
    doc = db["product"].find_one({"_id": to_obj_id(product_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize(doc)


@app.patch("/api/products/{product_id}")
def update_product(product_id: str, payload: dict):
    res = db["product"].update_one({"_id": to_obj_id(product_id)}, {"$set": payload})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    doc = db["product"].find_one({"_id": to_obj_id(product_id)})
    return serialize(doc)


@app.delete("/api/products/{product_id}")
def delete_product(product_id: str):
    res = db["product"].delete_one({"_id": to_obj_id(product_id)})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"ok": True}


# Reviews
@app.post("/api/reviews", response_model=dict)
def create_review(review: Review):
    review_id = create_document("review", review)
    return {"id": review_id}


@app.get("/api/reviews", response_model=List[dict])
def list_reviews(product_id: Optional[str] = None, user_id: Optional[str] = None, limit: Optional[int] = 100):
    query = {}
    if product_id:
        query["product_id"] = product_id
    if user_id:
        query["user_id"] = user_id
    docs = get_documents("review", query, limit)
    return [serialize(d) for d in docs]


# Cart
@app.get("/api/cart/{user_id}", response_model=dict)
def get_cart(user_id: str):
    doc = db["cart"].find_one({"user_id": user_id})
    if not doc:
        # create empty cart
        cart = Cart(user_id=user_id, items=[])
        cart_id = create_document("cart", cart)
        doc = db["cart"].find_one({"_id": ObjectId(cart_id)})
    return serialize(doc)


class CartItemModel(BaseModel):
    product_id: str
    qty: int


@app.post("/api/cart/{user_id}/add")
def add_to_cart(user_id: str, item: CartItemModel):
    cart = db["cart"].find_one({"user_id": user_id})
    if not cart:
        cart = {"user_id": user_id, "items": []}
        db["cart"].insert_one(cart)
    # check if exists
    found = False
    for it in cart.get("items", []):
        if it["product_id"] == item.product_id:
            it["qty"] = it.get("qty", 1) + item.qty
            found = True
            break
    if not found:
        cart.setdefault("items", []).append({"product_id": item.product_id, "qty": item.qty})
    db["cart"].update_one({"_id": cart["_id"]}, {"$set": {"items": cart["items"]}})
    return serialize(db["cart"].find_one({"_id": cart["_id"]}))


@app.post("/api/cart/{user_id}/remove")
def remove_from_cart(user_id: str, item: CartItemModel):
    cart = db["cart"].find_one({"user_id": user_id})
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    cart["items"] = [it for it in cart.get("items", []) if it["product_id"] != item.product_id]
    db["cart"].update_one({"_id": cart["_id"]}, {"$set": {"items": cart["items"]}})
    return serialize(db["cart"].find_one({"_id": cart["_id"]}))


# Orders
class CheckoutPayload(BaseModel):
    user_id: str


@app.post("/api/checkout", response_model=dict)
def checkout(payload: CheckoutPayload):
    cart = db["cart"].find_one({"user_id": payload.user_id})
    if not cart or not cart.get("items"):
        raise HTTPException(status_code=400, detail="Cart is empty")
    # Build order items with prices from products
    order_items = []
    total = 0.0
    for it in cart["items"]:
        prod = db["product"].find_one({"_id": to_obj_id(it["product_id"])})
        if not prod:
            continue
        price = float(prod.get("price", 0))
        qty = int(it.get("qty", 1))
        total += price * qty
        order_items.append({
            "product_id": it["product_id"],
            "qty": qty,
            "price": price
        })
    order = Order(user_id=payload.user_id, items=order_items, total=round(total, 2), status="paid")
    order_id = create_document("order", order)
    # empty cart
    db["cart"].update_one({"_id": cart["_id"]}, {"$set": {"items": []}})
    return {"id": order_id, "total": order.total, "status": order.status}


@app.get("/api/orders", response_model=List[dict])
def list_orders(user_id: Optional[str] = None, limit: Optional[int] = 50):
    query = {"user_id": user_id} if user_id else {}
    docs = get_documents("order", query, limit)
    return [serialize(d) for d in docs]


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
