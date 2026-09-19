"""
Payment integration endpoints.
Mocks payments by default unless STRIPE_SECRET_KEY or RAZORPAY_KEY_ID are set in config.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/payment", tags=["payment"])


class PaymentRequest(BaseModel):
    session_id: str
    amount_inr: float


@router.post("/initiate")
async def initiate_payment(req: PaymentRequest):
    """
    Creates a payment intent (Stripe) or order (Razorpay).
    Falls back to a mock success response if keys are not configured.
    """
    if settings.STRIPE_SECRET_KEY:
        # Pseudo-code for Stripe Integration
        # import stripe
        # stripe.api_key = settings.STRIPE_SECRET_KEY
        # intent = stripe.PaymentIntent.create(
        #     amount=int(req.amount_inr * 100),
        #     currency="inr",
        #     metadata={"session_id": req.session_id}
        # )
        # return {"provider": "stripe", "client_secret": intent.client_secret}
        pass

    if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
        # Pseudo-code for Razorpay Integration
        # import razorpay
        # client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        # order = client.order.create({
        #     "amount": int(req.amount_inr * 100),
        #     "currency": "INR",
        #     "receipt": f"receipt_{req.session_id}"
        # })
        # return {"provider": "razorpay", "order_id": order["id"]}
        pass

    # Mock fallback
    return {
        "provider": "mock",
        "status": "success",
        "transaction_id": f"txn_{uuid.uuid4().hex[:8]}",
        "message": "Payment mocked successfully (no active keys configured)"
    }
