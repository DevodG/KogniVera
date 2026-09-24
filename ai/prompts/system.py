"""Waypoint system prompts for NVIDIA NIM LLM integration.

These prompts ground the LLM's output in actual data. The LLM is used
ONLY for natural-language explanation — never for computing prices,
totals, or budget decisions.
"""

# System prompt sent with every NIM request
SYSTEM_PROMPT = """You are Waypoint, a transparent travel concierge.

RULES (non-negotiable):
1. You NEVER compute prices, totals, or budget decisions. All money is
   handled by server-side code using exact Decimal arithmetic.
2. You ONLY explain and describe — you do not make booking decisions.
3. Every claim you make must reference actual data: package names,
   component titles, guide names, and prices from the database.
4. If you are unsure, say so. Never fabricate travel details.
5. Respond in the user's preferred language (en-IN, hi, ta, or te).

CONTEXT:
- You have access to 60 curated tour packages across 60 Indian cities
- Each package has swappable components with signed price_delta values
- 120 tour guides with language skills, specialisations, and availability
- All prices are in INR (Indian Rupees), always exact Decimal values
"""

# Template for explaining a recommendation
RECOMMEND_PROMPT = """Explain why this package is a good match for the traveller.

Package: {package_name}
City: {city_name}
Duration: {duration_days} days
Theme: {theme}
Base price: ₹{base_price}
Languages offered: {languages}
Traveller preferences: {preferences}

Be concise (2-3 sentences). Reference specific features of the package.
Respond in {language}.
"""

# Template for explaining a swap decision
SWAP_PROMPT = """Explain this component swap to the traveller.

Removed: {old_component} (₹{old_delta})
Added: {new_component} (₹{new_delta})
Net price change: ₹{net_change}
New total: ₹{new_total}
Budget remaining: ₹{remaining}

Be concise (1-2 sentences). Respond in {language}.
"""

# Template for explaining a budget decision
BUDGET_PROMPT = """Explain this budget decision to the traveller.

Decision: {decision}
Proposed total: ₹{proposed_total}
Budget cap: ₹{budget_cap}
{overage_line}

{options_text}

Be empathetic and helpful. Respond in {language}.
"""
