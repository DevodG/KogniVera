import { useT } from "../i18n.jsx";

export default function LanguageSwitcher() {
  const { lang, setLang, t } = useT();

  const handleLanguageChange = (e) => {
    setLang(e.target.value);
  };

  return (
    <div style={{ display: "inline-block", position: "relative" }}>
      <select
        value={lang}
        onChange={handleLanguageChange}
        style={{
          appearance: "none",
          background: "var(--panel-sunken)",
          border: "1px solid var(--line)",
          borderRadius: "16px",
          color: "var(--ink)",
          padding: "4px 28px 4px 12px",
          fontSize: "12px",
          cursor: "pointer",
          outline: "none",
        }}
      >
        <option value="en-IN">{t("lang.en-IN")}</option>
        <option value="hi">{t("lang.hi")}</option>
        <option value="ta">{t("lang.ta")}</option>
        <option value="te">{t("lang.te")}</option>
      </select>
      <div
        style={{
          position: "absolute",
          right: "10px",
          top: "50%",
          transform: "translateY(-50%)",
          pointerEvents: "none",
          fontSize: "10px",
          color: "var(--dim)",
        }}
      >
        ▼
      </div>
    </div>
  );
}
