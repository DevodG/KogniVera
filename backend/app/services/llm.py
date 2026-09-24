"""NVIDIA NIM (OpenAI-Compatible) Multilingual LLM Service.

Provides natural language reasoning and multilingual explanations (English,
Hindi, Tamil, Telugu) for the transparent travel agent.

Non-negotiable grounding constraints:
1. The LLM NEVER computes prices, totals, or budget decisions. All money is
   handled strictly by Decimal and BudgetGuard in code.
2. If no API key is configured, or if the external service fails, the service
   falls back seamlessly to deterministic, grounded template reasoning.
"""
from __future__ import annotations

import os
from typing import Any, Optional
import httpx

from .. import config

DEFAULT_NIM_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_NIM_MODEL = "meta/llama-3.1-70b-instruct"

# Deterministic multilingual fallback templates
TEMPLATES: dict[str, dict[str, str]] = {
    "en-IN": {
        "plan": "Waypoint published its 5-step intent before querying any package data: (1) Find eligible packages, (2) Deterministic ranking, (3) Itinerary customization & guide matching, (4) Continuous Budget Guard checks, (5) Explicit user confirmation.",
        "rec": "Selected because this {duration_days}-day itinerary matches your {theme} preference in {city_name} with verified {language} support and fits comfortably within your budget cap.",
    },
    "hi": {
        "plan": "वेपॉइंट ने डेटा पढ़ने से पहले अपनी 5-चरणीय योजना प्रकाशित की: (1) योग्य पैकेज खोजना, (2) पारदर्शी रैंकिंग, (3) यात्रा कार्यक्रम और गाइड चयन, (4) निरंतर बजट गार्ड सत्यापन, (5) आपकी स्पष्ट स्वीकृति।",
        "rec": "यह {duration_days}-दिवसीय पैकेज आपकी {theme} थीम और {city_name} गंतव्य से पूरी तरह मेल खाता है, जिसमें {language} भाषा सहायता और बजट सीमा का पूर्ण पालन शामिल है।",
    },
    "ta": {
        "plan": "வேபாயிண்ட் எந்தவொரு தரவையும் படிப்பதற்கு முன் தனது 5-படி திட்டத்தை வெளியிட்டது: (1) தகுதியான தொகுப்புகளைத் தேடுதல், (2) வெளிப்படையான தரவரிசை, (3) பயணத் தனிப்பயனாக்கம் மற்றும் வழிகாட்டி தேர்வு, (4) தொடர்ச்சியான பட்ஜெட் காவலாளி சரிபார்ப்பு, (5) உங்களின் வெளிப்படையான ஒப்புதல்.",
        "rec": "இந்த {duration_days} நாட்கள் தொகுப்பு {city_name}-ல் உங்கள் {theme} விருப்பத்திற்கும் {language} மொழி ஆதரவிற்கும் பொருந்துகிறது மற்றும் உங்கள் பட்ஜெட் வரம்பிற்குள் உள்ளது.",
    },
    "te": {
        "plan": "వేపాయింట్ డేటాను చదవడానికి ముందే తన 5-దశల ప్రణాళికను ప్రచురించింది: (1) అర్హతగల ప్యాకేజీల గుర్తింపు, (2) పారదర్శక ర్యాంకింగ్, (3) ప్రయాణ మార్పులు & గైడ్ ఎంపిక, (4) నిరంతర బడ్జెట్ గార్డ్ తనిఖీలు, (5) మీ స్పష్టమైన నిర్ధారణ.",
        "rec": "ఈ {duration_days} రోజుల ప్యాకేజీ {city_name}లో మీ {theme} ప్రాధాన్యతకు మరియు {language} భాషా మద్దతుకు సరిగ్గా సరిపోతుంది, మీ బడ్జెట్ పరిమితికి కట్టుబడి ఉంటుంది.",
    },
}


class NvidiaNimService:
    """NVIDIA NIM inference service with deterministic multilingual fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or config.AI_API_KEY or os.getenv("NVIDIA_API_KEY")
        self.base_url = (base_url or config.AI_BASE_URL or DEFAULT_NIM_URL).rstrip("/")
        self.model = model or config.AI_MODEL or DEFAULT_NIM_MODEL
        self.is_configured = bool(self.api_key)

    def explain_plan(self, language: str = "en-IN") -> str:
        """Provide a concise explanation of the agent's intent in the requested language."""
        lang_key = self._resolve_lang_key(language)
        fallback = TEMPLATES.get(lang_key, TEMPLATES["en-IN"])["plan"]

        if not self.is_configured:
            return fallback

        system_prompt = (
            "You are Waypoint, a transparent travel concierge. Explain the 5-step transparent plan "
            f"in concise {self._lang_name(lang_key)} without mentioning any prices or numbers. "
            "Reinforce that no action is taken without explicit user consent."
        )
        try:
            return self._call_nim(system_prompt, "Explain the travel plan.") or fallback
        except Exception:
            return fallback

    def explain_recommendation(
        self,
        pkg_name: str,
        city_name: str,
        duration_days: int,
        theme: str,
        languages_offered: list[str],
        traveler_goal: Optional[str] = None,
        language: str = "en-IN",
    ) -> str:
        """Explain why a package was recommended, personalized to the traveller's goal."""
        lang_key = self._resolve_lang_key(language)
        template = TEMPLATES.get(lang_key, TEMPLATES["en-IN"])["rec"]
        fallback = template.format(
            duration_days=duration_days,
            city_name=city_name,
            theme=theme or "travel",
            language=", ".join(languages_offered) or "regional",
        )

        if not self.is_configured:
            return fallback

        system_prompt = (
            f"You are Waypoint. In 2 concise sentences in {self._lang_name(lang_key)}, explain why "
            f"the package '{pkg_name}' ({duration_days} days, {theme} in {city_name}) is an ideal match "
            f"for a traveler wanting: '{traveler_goal or 'a relaxed tour'}'. "
            "CRITICAL: Never mention prices, costs, or currency amounts. Only describe the travel fit."
        )
        try:
            return self._call_nim(system_prompt, f"Recommend {pkg_name}.") or fallback
        except Exception:
            return fallback

    def _call_nim(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 150,
            },
            timeout=4.0,
        )
        if resp.status_code == 200:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
        return None

    @staticmethod
    def _resolve_lang_key(bcp47: str) -> str:
        tag = (bcp47 or "en-IN").lower()
        if "hi" in tag:
            return "hi"
        if "ta" in tag:
            return "ta"
        if "te" in tag:
            return "te"
        return "en-IN"

    @staticmethod
    def _lang_name(key: str) -> str:
        names = {"hi": "Hindi", "ta": "Tamil", "te": "Telugu", "en-IN": "English"}
        return names.get(key, "English")
