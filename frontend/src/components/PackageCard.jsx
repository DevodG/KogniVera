import { formatMoney } from "../money.js";

const THEME_LABELS = {
  heritage: "Heritage",
  pilgrimage: "Pilgrimage",
  food_trail: "Food trail",
  adventure: "Adventure",
  wildlife: "Wildlife",
  wellness: "Wellness",
  honeymoon: "Honeymoon",
  family: "Family",
};

export default function PackageCard({ pkg, rank, onChoose, onView, chosen, busy }) {
  const over = !pkg.within_budget;
  return (
    <div className={`pkg ${rank === 1 ? "pkg--top" : ""}`}>
      <div className="pkg__head">
        <div>
          <h3 className="pkg__name">
            {pkg.name}
            {rank === 1 ? <span className="tag tag--theme">best match</span> : null}
          </h3>
          <p className="pkg__meta">
            {pkg.city_name} · {THEME_LABELS[pkg.theme] || pkg.theme} · {pkg.tier} ·{" "}
            {pkg.duration_days} days / {pkg.duration_nights} nights · groups{" "}
            {pkg.min_group_size}–{pkg.max_group_size}
          </p>
        </div>
        <div className="pkg__price">
          {formatMoney(pkg.included_total, pkg.currency)}
          <small>included total</small>
          <small style={{ color: over ? "var(--red)" : "var(--text-faint)" }}>
            base {formatMoney(pkg.base_price, pkg.currency)}
          </small>
        </div>
      </div>
      <div className="pkg__tags">
        {pkg.languages_offered.map((lang) => (
          <span className="tag tag--lang" key={lang}>
            {lang}
          </span>
        ))}
        <span className="tag">match score {pkg.match_score}</span>
        {over ? <span className="tag" style={{ color: "var(--red)" }}>over your cap</span> : null}
      </div>
      <p className="pkg__meta" style={{ marginBottom: 8 }}>
        {pkg.description}
      </p>
      <ul className="pkg__reasons">
        {pkg.match_reasons.map((r, i) => (
          <li key={i}>{r}</li>
        ))}
      </ul>
      <p className="tiny muted" style={{ margin: "10px 0 0" }}>
        <strong>Inclusions:</strong> {pkg.inclusions}
      </p>
      <p className="tiny muted" style={{ margin: "4px 0 0" }}>
        <strong>Exclusions:</strong> {pkg.exclusions}
      </p>
      <div className="pkg__actions">
        <button
          className="btn btn--primary"
          onClick={() => onChoose(pkg.package_id)}
          disabled={busy || chosen}
        >
          {chosen ? "✓ chosen" : "Choose package"}
        </button>
        {onView ? (
          <button className="btn btn--ghost" onClick={() => onView(pkg)} disabled={busy}>
            View itinerary
          </button>
        ) : null}
      </div>
    </div>
  );
}
