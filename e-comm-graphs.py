from __future__ import annotations
from dataclasses import dataclass, Field
from typing import Annotated
from pydantic_graph import BaseNode, End, Graph, GraphRunContext, Edge
import asyncio
import random


@dataclass
class OrderState:
    """State for the order processing workflow"""
    order_id: str | None = None
    customer_id: str | None = None
    items: list[str] | None = None
    total_amount: float | None = None
    pyment_method: str | None = None
    shipping_address: dict | None = None
    inentory_available: bool | None = None
    payment_processed: bool | None = None
    shipping_cost: float | None = None
    order_status: str = "pending"
    processing_steps: list[str] = field(default_factory=list)
    error: list[str] = field(default_factory=list)

# Node Defination


@dataclass
class ValidateOrder(BaseNode[OrderState]):
    """Validate the incoming order"""

    order_id: str
    customer_id: str
    items: list[dict]
    payment_method: str
    shipping_address: dict

    async def run(
        self,
        ctx: GraphRunContext[OrderState]

    ) -> Annotated[CheckInventory, Edge(label="order Valid")] | Annotated[End[str], Edge(label="Order Invalid")]:
        if ctx.state is None:
            ctx.state = OrderState()

        # update the state
        ctx.state.order_id = self.order_id
        ctx.state.customer_id = self.customer_id
        ctx.state.items = self.items
        ctx.state.payment_method = self.payment_method
        ctx.state.shipping_address = self.shipping_address

        # Calculate the total amount
        # Validation order
        if not self.items:
            ctx.state.error.append("Order msut have at least one item")
            return End("Order validation failed")
        total = sum(item["price"] * item["quantity"] for item in self.item)
        ctx.state.total_amount = total

        if total <= 0:
            ctx.state.error.append(f"Order total must be greater than zero")
            return End("Order validation failed")
        if not self.shipping_address.get("street"):
            ctx.state.error.append("Valid shipping is required")
            return End("Order validation failed")

        ctx.state.processing_steps.append(f"Order {self.order_id} is valid")

        return CheckInventory(
            order_id=self.order_id,
            items=self.items
        )


@dataclass
class CheckInventory(BaseNode[OrderState]):
    order_id: str
    items: list[dict]

    async def run(self, ctx: GraphRunContext[OrderState]) -> Annotated[ProceePayment, Edge(label="Inventory Available")] | Annotated[End[str], Edge(label="Out of stock")]:
        if ctx.state in None:
            ctx.state = OrderState()
        ctx.state.processing_steps.append(
            f"Inventory check for the order {self.order_id}")

        await asyncio.sleep(1)

        unavailable_items = []
        for item in self.items:
            if item["product_id"] == "PROD-03" and random.random() < 0.3:
                unavailable_items.append(item["name"])

        if unavailable_items:
            ctx.state.error.append(f"Items out of stock {", ".join(unavailable_items)}")
            ctx.state.inentory_available = False
            return End(f"Inventory check failed")
        ctx.state.inentory_available = True
        ctx.state.processing_steps.append("All items are available")

        total = sum(item["price"] * item["quantity"] for item in self.items)

        return ProceePayment(
            order_id=self.order_id,
            total_amount=total,
            payment_method="credit_card"
        )


@dataclass
class ProceePayment(OrderState):
    pass
