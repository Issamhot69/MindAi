import os
import stripe
from datetime import datetime, date
from core.database import SessionLocal, User

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_VOTRE_CLE")

PLANS = {
    "free": {"prix": 0, "images": 5, "voix": 5, "videos": 1},
    "pro": {"prix": 19, "images": 999, "voix": 999, "videos": 50},
    "enterprise": {"prix": 99, "images": 9999, "voix": 9999, "videos": 500},
}

# Compteur journalier simple
daily_usage = {}

def check_limit(user_id: str, plan: str, feature: str) -> bool:
    today = date.today().isoformat()
    key = f"{user_id}:{today}:{feature}"
    current = daily_usage.get(key, 0)
    limit = PLANS.get(plan, PLANS["free"]).get(feature, 0)
    return current < limit

def increment_usage(user_id: str, feature: str):
    today = date.today().isoformat()
    key = f"{user_id}:{today}:{feature}"
    daily_usage[key] = daily_usage.get(key, 0) + 1

def get_usage(user_id: str, plan: str) -> dict:
    today = date.today().isoformat()
    result = {}
    for feature in ["images", "voix", "videos"]:
        key = f"{user_id}:{today}:{feature}"
        current = daily_usage.get(key, 0)
        limit = PLANS.get(plan, PLANS["free"]).get(feature, 0)
        result[feature] = {"used": current, "limit": limit}
    return result

def create_checkout(plan: str, user_email: str) -> str:
    prices = {"pro": 1900, "enterprise": 9900}
    if plan not in prices:
        return None
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"AI Mind {plan.title()}"},
                "unit_amount": prices[plan],
                "recurring": {"interval": "month"},
            },
            "quantity": 1,
        }],
        mode="subscription",
        success_url="http://localhost:8035/studio?success=1",
        cancel_url="http://localhost:8035/pricing?cancel=1",
        customer_email=user_email,
    )
    return session.url
