"""
Advanced example demonstrating field exclusion with complex generic types.

This example shows how to exclude fields from multiple type parameters
in generic types like Dict[KeyType, ValueType] or Union[Type1, Type2].
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Annotated, Dict, Union
from uuid import UUID, uuid4

from litestar import Litestar, post
from litestar.dto import DTOConfig, DataclassDTO


@dataclass
class Product:
    """Product with pricing information."""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    price: float = 0.0
    internal_cost: float = 0.0  # Should be excluded from public API


@dataclass
class Category:
    """Product category."""
    id: UUID = field(default_factory=uuid4) 
    name: str = ""
    internal_code: str = ""  # Should be excluded from public API


@dataclass
class Store:
    """Store with products organized by categories."""
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    
    # Dictionary mapping category names to lists of products
    # Type is Dict[str, list[Product]] - a complex generic type
    inventory: Dict[str, list[Product]] = field(default_factory=dict)
    
    # List of category objects
    categories: list[Category] = field(default_factory=list)
    
    # Union type example - either a featured product or None
    featured_item: Union[Product, None] = None


# Configuration demonstrating complex exclusions
config = DTOConfig(
    exclude={
        "id",  # Exclude store id
        
        # Exclude internal_cost from products in inventory values
        # inventory is Dict[str, list[Product]]
        # - First type parameter (0) is str (the key) 
        # - Second type parameter (1) is list[Product] (the value)
        # - We want to exclude from Product, which is type parameter 0 of list[Product]
        "inventory.1.0.internal_cost",  # 1=list[Product], 0=Product, internal_cost=field
        "inventory.1.0.id",             # Also exclude product IDs from inventory
        
        # Exclude internal_code from categories
        # categories is list[Category]
        # - Type parameter 0 is Category
        "categories.0.internal_code",   # 0=Category, internal_code=field
        "categories.0.id",              # Also exclude category IDs
        
        # Exclude from featured_item (Union[Product, None])
        # featured_item is Union[Product, None]  
        # - Type parameter 0 is Product
        # - Type parameter 1 is None (nothing to exclude)
        "featured_item.0.internal_cost", # 0=Product, internal_cost=field
        "featured_item.0.id",            # Also exclude featured product ID
    }
)

StoreDTO = DataclassDTO[Store]
PublicStoreDTO = DataclassDTO[Annotated[Store, config]]


@post("/stores", dto=StoreDTO, return_dto=PublicStoreDTO, sync_to_thread=False)
def create_store(data: Store) -> Store:
    """
    Create a store with sample inventory.
    
    This demonstrates how exclusions work with complex nested generics.
    """
    # Create sample products with internal costs
    laptop = Product(
        name="Gaming Laptop",
        price=1200.0,
        internal_cost=800.0  # This will be excluded from response
    )
    
    mouse = Product(
        name="Wireless Mouse", 
        price=50.0,
        internal_cost=15.0   # This will be excluded from response
    )
    
    # Create categories with internal codes
    electronics = Category(
        name="Electronics",
        internal_code="ELEC-001"  # This will be excluded from response
    )
    
    accessories = Category(
        name="Accessories", 
        internal_code="ACC-001"   # This will be excluded from response
    )
    
    # Set up inventory (Dict[str, list[Product]])
    data.inventory = {
        "electronics": [laptop],
        "accessories": [mouse]
    }
    
    data.categories = [electronics, accessories]
    data.featured_item = laptop  # Union[Product, None]
    
    return data


app = Litestar(route_handlers=[create_store])

# Example output with exclusions:
# {
#   "name": "Tech Store",
#   "inventory": {
#     "electronics": [
#       {
#         "name": "Gaming Laptop",
#         "price": 1200.0
#         // "id" and "internal_cost" excluded
#       }
#     ],
#     "accessories": [
#       {
#         "name": "Wireless Mouse", 
#         "price": 50.0
#         // "id" and "internal_cost" excluded
#       }
#     ]
#   },
#   "categories": [
#     {
#       "name": "Electronics"
#       // "id" and "internal_code" excluded
#     },
#     {
#       "name": "Accessories"
#       // "id" and "internal_code" excluded  
#     }
#   ],
#   "featured_item": {
#     "name": "Gaming Laptop",
#     "price": 1200.0
#     // "id" and "internal_cost" excluded
#   }
# }