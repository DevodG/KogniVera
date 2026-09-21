import React, { createContext, useContext, useState } from "react";

const translations = {
  "en-IN": {
    "app.title": "Waypoint",
    "app.subtitle": "agentic travel concierge",
    "form.goal": "State your goal.",
    "form.goal_desc": "The agent will show you its plan before it acts, search real tools, and never cross the budget you set below without asking you first.",
    "form.trip_goal": "Trip goal",
    "form.origin": "Origin (IATA)",
    "form.destination": "Destination (IATA)",
    "form.depart": "Depart",
    "form.return": "Return",
    "form.travelers": "Travelers",
    "form.budget": "Budget cap (INR)",
    "form.submit": "Send the agent to work →",
    "form.planning": "Planning…",
    "step.details": "Details",
    "step.flight": "Flight",
    "step.hotel": "Hotel",
    "step.review": "Review",
    "lang.en-IN": "English (IN)",
    "lang.hi": "हिन्दी (Hindi)",
    "lang.ta": "தமிழ் (Tamil)",
    "lang.te": "తెలుగు (Telugu)",
  },
  "hi": {
    "app.title": "वेपॉइंट",
    "app.subtitle": "एजेंटिक यात्रा कंसीयज",
    "form.goal": "अपना लक्ष्य बताएं।",
    "form.goal_desc": "एजेंट कार्य करने से पहले आपको अपनी योजना दिखाएगा, वास्तविक उपकरण खोजेगा, और बिना आपसे पूछे आपके द्वारा निर्धारित बजट को कभी पार नहीं करेगा।",
    "form.trip_goal": "यात्रा का लक्ष्य",
    "form.origin": "मूल (IATA)",
    "form.destination": "गंतव्य (IATA)",
    "form.depart": "प्रस्थान",
    "form.return": "वापसी",
    "form.travelers": "यात्री",
    "form.budget": "बजट सीमा (INR)",
    "form.submit": "एजेंट को काम पर भेजें →",
    "form.planning": "योजना बना रहा है…",
    "step.details": "विवरण",
    "step.flight": "उड़ान",
    "step.hotel": "होटल",
    "step.review": "समीक्षा",
    "lang.en-IN": "English (IN)",
    "lang.hi": "हिन्दी (Hindi)",
    "lang.ta": "தமிழ் (Tamil)",
    "lang.te": "తెలుగు (Telugu)",
  },
  "ta": {
    "app.title": "வேபாயிண்ட்",
    "app.subtitle": "ஏஜென்டிக் பயண கன்சீர்ஜ்",
    "form.goal": "உங்கள் இலக்கை குறிப்பிடவும்.",
    "form.goal_desc": "ஏஜென்ட் செயல்படுவதற்கு முன்பு அதன் திட்டத்தை உங்களுக்குக் காண்பிக்கும், உண்மையான கருவிகளைத் தேடும், மற்றும் உங்களிடம் கேட்காமல் நீங்கள் அமைத்த பட்ஜெட்டை ஒருபோதும் தாண்டாது.",
    "form.trip_goal": "பயண இலக்கு",
    "form.origin": "புறப்படும் இடம் (IATA)",
    "form.destination": "சேருமிடம் (IATA)",
    "form.depart": "புறப்பாடு",
    "form.return": "திரும்புதல்",
    "form.travelers": "பயணிகள்",
    "form.budget": "பட்ஜெட் வரம்பு (INR)",
    "form.submit": "ஏஜென்ட்டை வேலைக்கு அனுப்பவும் →",
    "form.planning": "திட்டமிடுகிறது…",
    "step.details": "விவரங்கள்",
    "step.flight": "விமானம்",
    "step.hotel": "ஹோட்டல்",
    "step.review": "மதிப்பாய்வு",
    "lang.en-IN": "English (IN)",
    "lang.hi": "हिन्दी (Hindi)",
    "lang.ta": "தமிழ் (Tamil)",
    "lang.te": "తెలుగు (Telugu)",
  },
  "te": {
    "app.title": "వేపాయింట్",
    "app.subtitle": "ఏజెంటిక్ ట్రావెల్ కన్సీర్జ్",
    "form.goal": "మీ లక్ష్యాన్ని పేర్కొనండి.",
    "form.goal_desc": "ఏజెంట్ పని చేసే ముందు దాని ప్లాన్‌ను మీకు చూపుతుంది, నిజమైన సాధనాలను శోధిస్తుంది మరియు మిమ్మల్ని అడగకుండా మీరు సెట్ చేసిన బడ్జెట్‌ను ఎప్పుడూ దాటదు.",
    "form.trip_goal": "ప్రయాణ లక్ష్యం",
    "form.origin": "మూలం (IATA)",
    "form.destination": "గమ్యం (IATA)",
    "form.depart": "బయలుదేరుట",
    "form.return": "తిరిగి రాక",
    "form.travelers": "ప్రయాణికులు",
    "form.budget": "బడ్జెట్ పరిమితి (INR)",
    "form.submit": "ఏజెంట్‌ను పనికి పంపండి →",
    "form.planning": "ప్లాన్ చేస్తోంది…",
    "step.details": "వివరాలు",
    "step.flight": "విమానం",
    "step.hotel": "హోటల్",
    "step.review": "సమీక్ష",
    "lang.en-IN": "English (IN)",
    "lang.hi": "हिन्दी (Hindi)",
    "lang.ta": "தமிழ் (Tamil)",
    "lang.te": "తెలుగు (Telugu)",
  }
};

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [lang, setLang] = useState("en-IN");

  const t = (key) => {
    return translations[lang]?.[key] || translations["en-IN"]?.[key] || key;
  };

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useT() {
  return useContext(LanguageContext);
}
