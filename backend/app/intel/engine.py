"""
The deterministic intelligence engine.

Why deterministic is the right primary engine here (not a fallback):
the team has no LLM credentials, the venue Wi-Fi is a known demo-killer, and
the rules demand "a genuine, working AI feature — not a mock". A scoring
engine over real rows, with every signal traceable to a column, is genuine
intelligence that cannot hallucinate and cannot go offline.

Design contract for every scorer:
  - Every score is 0.0-1.0 and is accompanied by REASONS: human-readable
    strings citing the exact data that moved it. No black boxes.
  - A low score is as informative as a high one — it says what is missing,
    which is what the negotiation/trace surfaces to the traveller.
  - Only real columns are read. Nothing is invented, averaged away, or
    defaulted to a plausible-looking constant.

The LLM layer (intel/llm.py) may sit ABOVE this and narrate the results, but
it can never override the scores — the deterministic engine is the source of
truth, by design.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.core.money import Money
from app.core.reprice import Component, Package, reprice, swap_delta
from app.data.packagepro import (
    get_component,
    get_components,
    get_package,
    get_packages,
    get_swap_alternatives,
    get_guides,
    guides_available_on,
)


@dataclass
class Reason:
    """One thing that moved a score, and by how much."""

    label: str
    delta: Decimal
    detail: str = ""


@dataclass
class Scored:
    """A scored candidate with its full reasoning trail."""

    score: Decimal
    reasons: list[Reason] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": str(self.score),
            "confidence": self._band(),
            "reasons": [
                {"label": r.label, "delta": str(r.delta), "detail": r.detail}
                for r in self.reasons
            ],
        }

    def _band(self) -> str:
        if self.score >= Decimal("0.75"):
            return "high"
        if self.score >= Decimal("0.5"):
            return "medium"
        return "low"


def _d(x: Decimal | float | int | str) -> Decimal:
    return Decimal(str(x))


# ---------------------------------------------------------------------------
# Traveler profile — the preference signal the scorers read
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Traveler:
    """The preference bundle. All fields optional — cold start must work."""

    languages: tuple[str, ...] = ()
    interests: tuple[str, ...] = ()       # category codes / themes
    budget_band: str = ""                 # shoestring..luxury
    travel_style: str = ""                # budget..wellness
    traveller_type: str = ""              # solo..backpacker
    pace: str = ""                        # relaxed..packed
    dietary_flags: tuple[str, ...] = ()
    accessibility_needs: tuple[str, ...] = ()
    preferred_currency: str = "INR"
    segment: str = ""                     # heavy / light / cold_start

    @classmethod
    def from_prefs_row(cls, row: dict) -> "Traveler":
        """Build from a user_preferences row (plus the users row)."""
        def tup(raw, field_name):
            if not raw:
                return ()
            vals = tuple(v.strip() for v in str(raw).split(",") if v.strip())
            return () if vals == ("none",) else vals

        return cls(
            languages=tup(row.get("preferred_languages"), "preferred_languages"),
            interests=tup(row.get("interests"), "interests"),
            dietary_flags=tup(row.get("dietary_flags"), "dietary_flags"),
            accessibility_needs=tup(row.get("accessibility_needs"), "accessibility_needs"),
            preferred_currency=row.get("preferred_currency") or "INR",
            pace=row.get("pace") or "",
        )


# ---------------------------------------------------------------------------
# 1. Package scoring
# ---------------------------------------------------------------------------

# Budget band -> approximate daily spend ceiling (relative, band-normalised).
_BAND_WEIGHT: dict[str, Decimal] = {
    "shoestring": Decimal("1.0"),
    "value": Decimal("0.85"),
    "mid": Decimal("0.65"),
    "premium": Decimal("0.35"),
    "luxury": Decimal("0.1"),
}
_THEME_TO_STYLE: dict[str, tuple[str, ...]] = {
    "adventure": ("adventure", "budget", "backpacker"),
    "honeymoon": ("luxury", "comfort", "couple"),
    "pilgrimage": ("cultural", "slow"),
    "family": ("comfort", "slow", "family"),
    "heritage": ("cultural", "slow", "comfort"),
    "wellness": ("wellness", "slow", "luxury"),
    "wildlife": ("adventure", "nature", "slow"),
    "food_trail": ("cultural", "food"),
}


def score_package(pkg: Package, traveler: Traveler) -> Scored:
    """
    Score one package against a traveler. Signals, each traceable:

      language   does the package offer a language they speak (R6)
      budget     does the per-day cost fit their budget band
      theme      does the theme match their travel style / traveller type
      pace       does duration match their stated pace
      party      does the group-size window fit their traveller type
    """
    reasons: list[Reason] = []
    score = Decimal("0.5")  # neutral start

    # --- language (the PS-04 filter; strongest signal) ---
    if traveler.languages:
        offered = pkg.languages_offered
        match = any(lang in offered for lang in traveler.languages)
        if match:
            hit = next(l for l in traveler.languages if l in offered)
            score += Decimal("0.25")
            reasons.append(Reason("language", Decimal("0.25"),
                                  f"package offers {hit} (languages_offered)"))
        else:
            score -= Decimal("0.3")
            reasons.append(Reason("language", Decimal("-0.3"),
                                  f"package offers {', '.join(offered[:3])}; no match for "
                                  f"{', '.join(traveler.languages[:3])}"))

    # --- budget: per-day cost vs band expectation ---
    per_day = pkg.base_price.amount / Decimal(max(1, pkg.duration_days))
    band_w = _BAND_WEIGHT.get(traveler.budget_band, Decimal("0.65")) if traveler.budget_band else None
    if band_w is not None:
        # Reference daily spend per band (INR-normalised; relative signal only).
        ref = Decimal("12000") * (Decimal("1") - band_w) + Decimal("1500")
        # affordability = expectation / actual. >=1 means within band.
        ratio = ref / per_day if per_day > 0 else Decimal("0")
        if ratio >= Decimal("1.0"):
            delta = Decimal("0.15")
        elif ratio >= Decimal("0.85"):
            delta = Decimal("0.02")   # slightly over band
        elif ratio >= Decimal("0.7"):
            delta = Decimal("-0.05")  # clearly over
        else:
            delta = Decimal("-0.2")   # far over band
        score += delta
        reasons.append(Reason("budget", delta,
                              f"{per_day.quantize(Decimal('0.01'))} {pkg.base_price.currency}/day "
                              f"vs {ref.quantize(Decimal('0'))} band expectation "
                              f"({traveler.budget_band})"))

    # --- theme vs travel style / traveller type ---
    styles = _THEME_TO_STYLE.get(pkg.theme, ())
    style_hit = traveler.travel_style in styles or traveler.traveller_type in styles
    if styles and (traveler.travel_style or traveler.traveller_type):
        delta = Decimal("0.12") if style_hit else Decimal("-0.08")
        score += delta
        reasons.append(Reason("theme", delta,
                              f"theme '{pkg.theme}' fits "
                              f"{traveler.travel_style or traveler.traveller_type}"))

    # --- pace: duration vs stated pace ---
    if traveler.pace and pkg.duration_days:
        want = {"relaxed": (5, 99), "balanced": (3, 6), "packed": (1, 3)}.get(traveler.pace)
        if want:
            lo, hi = want
            inside = lo <= pkg.duration_days <= hi
            delta = Decimal("0.08") if inside else Decimal("-0.05")
            score += delta
            reasons.append(Reason("pace", delta,
                                  f"{pkg.duration_days} days vs {traveler.pace} window "
                                  f"({lo}-{hi})"))

    # --- party size window vs traveller type ---
    if traveler.traveller_type:
        familyish = traveler.traveller_type in ("family", "friends")
        fits = (pkg.max_group_size >= (4 if familyish else 2)) and pkg.min_group_size <= 5
        delta = Decimal("0.05") if fits else Decimal("0")
        score += delta
        if delta:
            reasons.append(Reason("party", delta,
                                  f"group window {pkg.min_group_size}-{pkg.max_group_size} "
                                  f"suits {traveler.traveller_type}"))

    # clamp
    score = max(Decimal("0"), min(Decimal("1"), score))
    return Scored(score=score, reasons=reasons)


def recommend_packages(traveler: Traveler, limit: int = 8) -> list[tuple[Package, Scored]]:
    """Rank packages for a traveler, best first, each with its reasoning."""
    pkgs = get_packages(limit=60)
    scored = [(p, score_package(p, traveler)) for p in pkgs]
    scored.sort(key=lambda ps: ps[1].score, reverse=True)
    return scored[:limit]


# ---------------------------------------------------------------------------
# 2. Swap advisor — which alternative should I pick?
# ---------------------------------------------------------------------------

def score_swap(
    current: Component,
    alt: Component,
    traveler: Traveler,
    budget_remaining: Money,
) -> Scored:
    """
    Score a candidate replacement. Signals:

      price      signed net delta of the swap (cheaper = better for a budget)
      budget     does it still fit the remaining cap
      language   if the component is a guide, does it speak their language
      fit        title/keyword overlap with the traveler's interests
    """
    reasons: list[Reason] = []
    score = Decimal("0.5")
    delta = swap_delta(current, alt)  # Decimal-exact

    # price signal
    if delta.amount < 0:
        score += Decimal("0.25")
        reasons.append(Reason("price", Decimal("0.25"),
                              f"saves {abs(delta).format()} vs current"))
    elif delta.amount == 0:
        reasons.append(Reason("price", Decimal("0"), "price-neutral swap"))
    else:
        score -= Decimal("0.15")
        reasons.append(Reason("price", Decimal("-0.15"),
                              f"costs {delta.format()} more than current"))

    # budget fit
    if delta.amount > 0:
        fits = delta.amount <= budget_remaining.amount
        delta_b = Decimal("0.1") if fits else Decimal("-0.35")
        score += delta_b
        reasons.append(Reason("budget", delta_b,
                              f"overage {delta.format()} vs remaining "
                              f"{budget_remaining.format()}"))

    # guide language
    if alt.component_type == "guide" and traveler.languages:
        # Resolve the guide's languages via the entity if resolvable; else keyword.
        langs = _guide_languages(alt)
        hit = any(l in langs for l in traveler.languages)
        delta_l = Decimal("0.2") if hit else Decimal("-0.2")
        score += delta_l
        reasons.append(Reason("language", delta_l,
                              f"guide offers {', '.join(langs[:3]) or 'n/a'}; "
                              f"preference {', '.join(traveler.languages[:2])}"))

    # interest fit by keyword overlap (interests are category codes / words)
    if traveler.interests:
        title_l = alt.title.lower()
        hits = [i for i in traveler.interests if i.lower() in title_l]
        if hits:
            score += Decimal("0.1")
            reasons.append(Reason("interest", Decimal("0.1"),
                                  f"title matches {', '.join(hits)}"))

    score = max(Decimal("0"), min(Decimal("1"), score))
    return Scored(score=score, reasons=reasons)


def advise_swap(
    component_id: str,
    traveler: Traveler,
    budget_remaining: Money,
    limit: int = 6,
) -> list[tuple[Component, Scored]]:
    """Rank the alternatives for a component, best first, with reasons."""
    current = get_component(component_id)
    if not current:
        return []
    alts = get_swap_alternatives(component_id)
    scored = [(a, score_swap(current, a, traveler, budget_remaining)) for a in alts]
    scored.sort(key=lambda ps: ps[1].score, reverse=True)
    return scored[:limit]


def _guide_languages(component: Component) -> list[str]:
    """Best-effort language lookup for a guide component (R6 tags or [])."""
    if component.entity_id and component.entity_id.startswith("gid_"):
        from app.data.packagepro import get_guide

        g = get_guide(component.entity_id)
        if g:
            return g["languages"]
    return []


# ---------------------------------------------------------------------------
# 3. Guide matcher
# ---------------------------------------------------------------------------

def score_guide(guide: dict, traveler: Traveler, on_date: str | None = None) -> Scored:
    """
    Score a guide. Signals:

      language   BCP-47 overlap with the traveler preference (R6)
      special    does the specialisation match an interest
      quality    rating + experience (capped so a 5.0 nobody is not #1)
      budget     day_rate vs budget band
      availability is a hard GATE, not a score — unavailable guides are excluded
                    upstream, never down-weighted, because 'free on the date'
                    is a factual query.
    """
    reasons: list[Reason] = []
    score = Decimal("0.4")

    # language
    if traveler.languages:
        langs = guide.get("languages") or []
        hit = next((l for l in traveler.languages if l in langs), None)
        if hit:
            score += Decimal("0.3")
            reasons.append(Reason("language", Decimal("0.3"),
                                  f"speaks {hit}"))
        else:
            score -= Decimal("0.25")
            reasons.append(Reason("language", Decimal("-0.25"),
                                  f"offers {', '.join(langs[:3])}; no {', '.join(traveler.languages[:2])}"))

    # specialisation vs interests
    spec = guide.get("specialisation") or ""
    if traveler.interests:
        if spec in traveler.interests:
            score += Decimal("0.2")
            reasons.append(Reason("specialisation", Decimal("0.2"),
                                  f"{spec} matches an interest"))
        elif guide.get("secondary_specialisation") in traveler.interests:
            score += Decimal("0.1")
            reasons.append(Reason("specialisation", Decimal("0.1"),
                                  f"secondary {guide['secondary_specialisation']} matches"))

    # quality: rating and experience, capped contribution
    rating = guide.get("rating")
    if rating is not None:
        r = _d(rating)
        delta = (r - Decimal("3.5")) * Decimal("0.06")
        delta = max(-Decimal("0.15"), min(Decimal("0.2"), delta))
        score += delta
        reasons.append(Reason("quality", delta, f"rating {r}"))
    exp = guide.get("years_experience") or 0
    if exp:
        delta = min(Decimal("0.08"), _d(exp) * Decimal("0.003"))
        score += delta
        reasons.append(Reason("quality", delta, f"{exp} years experience"))

    if guide.get("certified"):
        score += Decimal("0.05")
        reasons.append(Reason("certified", Decimal("0.05"), "certified guide"))

    # budget
    if traveler.budget_band and guide.get("day_rate"):
        w = _BAND_WEIGHT.get(traveler.budget_band, Decimal("0.65"))
        ref = Decimal("4000") * (Decimal("1") - w) + Decimal("800")
        rate = guide["day_rate"].amount
        if rate <= ref:
            score += Decimal("0.1")
            reasons.append(Reason("budget", Decimal("0.1"),
                                  f"day rate {guide['day_rate'].format()} within band"))
        else:
            score -= Decimal("0.1")
            reasons.append(Reason("budget", Decimal("-0.1"),
                                  f"day rate {guide['day_rate'].format()} above band"))

    score = max(Decimal("0"), min(Decimal("1"), score))
    return Scored(score=score, reasons=reasons)


def recommend_guides(
    traveler: Traveler,
    on_date: str | None = None,
    city_id: str | None = None,
    limit: int = 6,
) -> list[tuple[dict, Scored]]:
    """
    Rank guides. Availability on `on_date` is a hard gate: a guide who is not
    free that day never appears, because 'is this guide free?' is a factual
    query against guide_availability, not an opinion.
    """
    langs = list(traveler.languages) or None
    if on_date:
        # Gate on real availability first.
        pool = guides_available_on(langs, None, on_date, city_id=city_id, limit=limit * 3)
    else:
        pool = get_guides(languages=langs, city_id=city_id, limit=limit * 3)

    scored = []
    for g in pool:
        s = score_guide(g, traveler, on_date)
        scored.append((g, s))
    scored.sort(key=lambda gs: gs[1].score, reverse=True)
    return scored[:limit]


# ---------------------------------------------------------------------------
# 4. Cold start — the honest signal
# ---------------------------------------------------------------------------

def explain_cold_start(traveler: Traveler) -> dict:
    """
    If the traveler has no preference signal, SAY so and base the ranking on
    declared data only. Faking confidence here would break the trust thesis.
    """
    has_lang = bool(traveler.languages)
    has_interests = bool(traveler.interests)
    has_band = bool(traveler.budget_band)
    signals = has_lang + has_interests + has_band
    if signals >= 2:
        return {"cold_start": False, "evidence": "ranking on declared preferences"}
    missing = [
        n for have, n in ((has_lang, "language"), (has_interests, "interests"), (has_band, "budget band"))
        if not have
    ]
    return {
        "cold_start": True,
        "evidence": (
            "new traveler — no travel history. Ranking on declared data only; "
            f"missing signals: {', '.join(missing) or 'none'}."
        ),
    }
