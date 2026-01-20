from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import Annotated

from pydantic_graph import BaseNode, End, Graph, GraphRunContext, Edge


# =========================
# STATE
# =========================

@dataclass
class OrderState:
    order_id: str | None = None
    customer_id: str | None = None
    items: list[dict] | None = None
    total_amount: float | None = None
    payment_method: str | None = None
    shipping_address: dict | None = None
    inventory_available: bool | None = None
    payment_processed: bool | None = None
    shipping_cost: float | None = None
    order_status: str = "pending"
    processing_steps: list[str] = field(default_factory=list)
    error: list[str] = field(default_factory=list)


# =========================
# NODES
# =========================

@dataclass
class ValidateOrder(BaseNode[OrderState]):
    order_id: str
    customer_id: str
    items: list[dict]
    payment_method: str
    shipping_address: dict

    async def run(self, ctx: GraphRunContext[OrderState]):
        if ctx.state is None:
            ctx.state = OrderState()

        ctx.state.order_id = self.order_id
        ctx.state.customer_id = self.customer_id
        ctx.state.items = self.items
        ctx.state.payment_method = self.payment_method
        ctx.state.shipping_address = self.shipping_address

        if not self.items:
            ctx.state.error.append("Order must have at least one item")
            return End("Validation failed")

        total = sum(i["price"] * i["quantity"] for i in self.items)
        if total <= 0:
            ctx.state.error.append("Invalid order total")
            return End("Validation failed")

        if not self.shipping_address.get("street"):
            ctx.state.error.append("Invalid shipping address")
            return End("Validation failed")

        ctx.state.total_amount = total
        ctx.state.processing_steps.append("Order validated")

        return CheckInventory(
            order_id=self.order_id,
            items=self.items,
            payment_method=self.payment_method,
        )


@dataclass
class CheckInventory(BaseNode[OrderState]):
    order_id: str
    items: list[dict]
    payment_method: str

    async def run(
        self, ctx: GraphRunContext[OrderState]
    ) -> Annotated["ProcessPayment", Edge("Inventory OK")] | Annotated[End[str], Edge("Out of stock")]:
        if ctx.state is None:
            ctx.state = OrderState()

        await asyncio.sleep(0.5)

        for item in self.items:
            product_id = item.get("product_id")
            if product_id == "PROD-03" and random.random() < 0.3:
                ctx.state.inventory_available = False
                ctx.state.error.append(f"Item {product_id} out of stock")
                return End("Inventory failed")

        ctx.state.inventory_available = True
        ctx.state.processing_steps.append("Inventory checked")

        return ProcessPayment(
            order_id=self.order_id,
            amount=ctx.state.total_amount or 0.0,
            payment_method=self.payment_method,
        )


@dataclass
class ProcessPayment(BaseNode[OrderState]):
    order_id: str
    amount: float
    payment_method: str

    async def run(
        self, ctx: GraphRunContext[OrderState]
    ) -> Annotated["CalculateShipping", Edge("Payment OK")] | Annotated[End[str], Edge("Payment Failed")]:
        if ctx.state is None:
            ctx.state = OrderState()

        if self.payment_method == "invalid":
            ctx.state.payment_processed = False
            ctx.state.error.append("Payment declined")
            return End("Payment failed")

        if self.amount > 1000 and random.random() < 0.1:
            ctx.state.payment_processed = False
            ctx.state.error.append("Payment declined")
            return End("Payment failed")

        ctx.state.payment_processed = True
        ctx.state.processing_steps.append("Payment processed")

        return CalculateShipping(
            order_id=self.order_id,
            shipping_address=ctx.state.shipping_address,
        )


@dataclass
class CalculateShipping(BaseNode[OrderState]):
    order_id: str
    shipping_address: dict

    async def run(
        self, ctx: GraphRunContext[OrderState]
    ) -> Annotated["ConfirmOrder", Edge("Shipping calculated")]:
        if ctx.state is None:
            ctx.state = OrderState()

        base = 10.0
        if self.shipping_address.get("country") != "US":
            shipping_cost = base + 25.0
        else:
            shipping_cost = base

        ctx.state.shipping_cost = shipping_cost
        ctx.state.processing_steps.append(f"Shipping cost: ${shipping_cost}")

        return ConfirmOrder(self.order_id, shipping_cost)


@dataclass
class ConfirmOrder(BaseNode[OrderState]):
    order_id: str
    shipping_cost: float

    async def run(
        self, ctx: GraphRunContext[OrderState]
    ) -> Annotated[End[str], Edge("Order confirmed")]:
        if ctx.state is None:
            ctx.state = OrderState()

        ctx.state.order_status = "confirmed"
        ctx.state.processing_steps.append("Order confirmed")

        return End("Success")


# =========================
# GRAPH
# =========================

order_processing_graph = Graph(
    nodes=[
        ValidateOrder,
        CheckInventory,
        ProcessPayment,
        CalculateShipping,
        ConfirmOrder,
    ],
    state_type=OrderState,
)


# =========================
# RUN
# =========================

async def main():
    start = ValidateOrder(
        order_id="ORD-001",
        customer_id="CUST-001",
        items=[
            {"product_id": "PROD-01", "name": "MacBook",
                "price": 999.0, "quantity": 1},
            {"product_id": "PROD-02", "name": "Mouse", "price": 29.0, "quantity": 2},
        ],
        payment_method="credit_card",
        shipping_address={
            "street": "123 Main St",
            "city": "SF",
            "state": "CA",
            "country": "US",
        },
    )

    result = await order_processing_graph.run(start)
    print(result.output)


if __name__ == "__main__":
    asyncio.run(main())
