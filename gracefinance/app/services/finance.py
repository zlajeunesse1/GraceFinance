"""
GraceFinance Core Financial Logic
Ported from your Streamlit prototype — this is the brain of the app.
"""

from app.models import TransactionCategory

# ============ TRANSACTION CATEGORIZER ============
# Ported directly from your categorize() function

CATEGORY_KEYWORDS = {
    TransactionCategory.RENT: ["rent"],
    TransactionCategory.FOOD: ["aldi", "big y", "market", "grocery", "restaurant",
                                "chipotle", "mcdonald", "wendy", "dunkin", "starbucks",
                                "doordash", "grubhub", "uber eats"],
    TransactionCategory.GAS: ["shell", "gulf", "exxon", "gas", "sunoco", "mobil",
                               "citgo", "bp"],
    TransactionCategory.CREDIT_CARDS: ["credit", "discover", "capital one"],
    TransactionCategory.INSURANCE: ["insurance", "geico", "progressive", "state farm",
                                     "allstate"],
    TransactionCategory.PHONE_BILL: ["verizon", "t-mobile", "phone", "at&t", "sprint"],
    TransactionCategory.UTILITIES: ["electric", "water", "sewer", "national grid",
                                     "eversource", "comcast", "xfinity", "spectrum"],
    TransactionCategory.INCOME: ["payroll", "direct deposit", "salary", "paycheck",
                                  "venmo", "zelle"],
}

# Categories that count as "needs" (from your NEEDS set)
NEEDS_CATEGORIES = {
    TransactionCategory.RENT,
    TransactionCategory.FOOD,
    TransactionCategory.GAS,
    TransactionCategory.CREDIT_CARDS,
    TransactionCategory.INSURANCE,
    TransactionCategory.PHONE_BILL,
    TransactionCategory.UTILITIES,
}


def categorize_transaction(description: str) -> TransactionCategory:
    """Auto-categorize a transaction based on description keywords."""
    desc_lower = description.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in desc_lower for keyword in keywords):
            return category

    return TransactionCategory.PERSONAL


def is_need(category: TransactionCategory) -> bool:
    """Determine if a transaction category is a need vs a want."""
    return category in NEEDS_CATEGORIES


# ============ AVALANCHE DEBT PAYDOWN ============
# Ported from your debt allocation code

def calculate_avalanche(debts: list[dict], available_for_debt: float) -> dict:
    """
    Avalanche method: pay minimums on everything, then throw all extra
    at the highest APR debt first.

    Args:
        debts: List of dicts with keys: name, balance, apr, min_payment
        available_for_debt: Total dollars available for debt this month

    Returns:
        dict with 'allocations' list and 'remaining' unallocated amount
    """
    debts_copy = [d.copy() for d in debts]
    remaining = max(available_for_debt, 0)
    allocations = []

    # Step 1: Pay minimums first
    for d in debts_copy:
        if d["balance"] <= 0:
            continue
        pay = min(d.get("min_payment", 0), d["balance"], remaining)
        if pay > 0:
            d["balance"] -= pay
            remaining -= pay
            allocations.append({
                "name": d["name"],
                "apr": d["apr"],
                "payment": round(pay, 2),
                "stage": "Minimum",
                "balance_after": round(d["balance"], 2),
            })

    # Step 2: Avalanche — highest APR gets all remaining
    debts_sorted = sorted(debts_copy, key=lambda x: x["apr"], reverse=True)
    for d in debts_sorted:
        if remaining <= 0 or d["balance"] <= 0:
            continue
        pay = min(d["balance"], remaining)
        d["balance"] -= pay
        remaining -= pay
        allocations.append({
            "name": d["name"],
            "apr": d["apr"],
            "payment": round(pay, 2),
            "stage": "Avalanche Extra",
            "balance_after": round(d["balance"], 2),
        })

    return {
        "allocations": allocations,
        "remaining": round(remaining, 2),
    }


def months_to_debt_free(debts: list[dict], monthly_payment: float) -> int | None:
    """
    Simulate month-by-month avalanche payments to find debt-free date.

    Returns number of months, or None if it would take 50+ years.
    """
    if monthly_payment <= 0:
        return None

    debts_copy = [d.copy() for d in debts]
    months = 0
    max_months = 600  # 50 years cap

    while months < max_months:
        total_balance = sum(d["balance"] for d in debts_copy)
        if total_balance <= 0.01:  # Close enough to zero
            break
        months += 1
        remaining = monthly_payment

        # Add interest + pay minimums
        for d in debts_copy:
            if d["balance"] <= 0:
                continue
            # Monthly interest accrual
            d["balance"] += d["balance"] * (d["apr"] / 12)
            pay = min(d.get("min_payment", 0), d["balance"], remaining)
            d["balance"] -= pay
            remaining -= pay

        # Avalanche extra to highest APR
        debts_sorted = sorted(debts_copy, key=lambda x: x["apr"], reverse=True)
        for d in debts_sorted:
            if remaining <= 0 or d["balance"] <= 0:
                continue
            pay = min(d["balance"], remaining)
            d["balance"] -= pay
            remaining -= pay

    return months if months < max_months else None


def calculate_credit_utilization(debts: list[dict]) -> dict:
    """Calculate overall and per-card credit utilization."""
    credit_cards = [d for d in debts if d.get("credit_limit") and d["credit_limit"] > 0]

    total_balance = sum(d["balance"] for d in credit_cards)
    total_limit = sum(d["credit_limit"] for d in credit_cards)

    overall = (total_balance / total_limit * 100) if total_limit > 0 else 0

    per_card = []
    for card in credit_cards:
        util = (card["balance"] / card["credit_limit"] * 100)
        per_card.append({
            "name": card["name"],
            "balance": card["balance"],
            "limit": card["credit_limit"],
            "utilization": round(util, 1),
        })

    return {
        "overall": round(overall, 1),
        "total_balance": total_balance,
        "total_limit": total_limit,
        "per_card": per_card,
    }


def calculate_spending_breakdown(transactions: list[dict]) -> dict:
    """Separate transactions into needs vs personal spending."""
    needs_total = 0.0
    personal_total = 0.0

    for txn in transactions:
        if txn["amount"] >= 0:  # Skip income
            continue
        abs_amount = abs(txn["amount"])
        if is_need(txn.get("category", TransactionCategory.PERSONAL)):
            needs_total += abs_amount
        else:
            personal_total += abs_amount

    return {
        "needs": round(needs_total, 2),
        "personal": round(personal_total, 2),
        "total": round(needs_total + personal_total, 2),
    }
