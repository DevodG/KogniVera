import { formatMoney } from "../money.js";

export default function GuideCard({ guide, onSelect, selected, busy }) {
  const unavailable = !guide.available;
  return (
    <div
      className={`guide ${unavailable ? "guide--unavailable" : ""} ${selected ? "guide--selected" : ""}`}
    >
      <div className="guide__head">
        <div>
          <h3 className="guide__name">
            {guide.display_name}
            {guide.certified ? <span className="tag tag--theme">certified</span> : null}
            {selected ? <span className="tag tag--lang">selected</span> : null}
          </h3>
          <p className="pkg__meta">
            {guide.specialisation}
            {guide.secondary_specialisation ? ` · ${guide.secondary_specialisation}` : ""} ·{" "}
            {guide.years_experience} yrs experience · {guide.review_count} reviews
            {guide.rating ? ` · rating ${guide.rating}` : " · unrated"}
          </p>
        </div>
        <div className="guide__rate">
          {formatMoney(guide.day_rate, guide.currency)}
          <small style={{ display: "block", color: "var(--text-faint)" }}>full day</small>
          <small style={{ color: "var(--text-faint)" }}>
            half day {formatMoney(guide.half_day_rate, guide.currency)}
          </small>
        </div>
      </div>
      <p className="guide__reason">{guide.fit_reason}</p>
      <div className="guide__avail">
        {guide.available_days.map((d) => (
          <span className="daychip daychip--free" key={`f-${d.for_date}`}>
            {d.for_date.slice(5)} ×{d.price_multiplier}
          </span>
        ))}
        {guide.unavailable_days.map((d) => (
          <span className="daychip daychip--busy" key={`b-${d.for_date}`}>
            {d.for_date.slice(5)} full
          </span>
        ))}
      </div>
      {unavailable ? (
        <div className="pkg__actions">
          <span className="decision decision--blocked">unavailable on your dates</span>
        </div>
      ) : (
        <div className="pkg__actions">
          <button
            className="btn btn--primary tiny"
            onClick={() => onSelect(guide.guide_id, "full_day")}
            disabled={busy || selected}
          >
            {selected ? "✓ guide added" : "Add guide · full day"}
          </button>
          <button
            className="btn tiny"
            onClick={() => onSelect(guide.guide_id, "half_day")}
            disabled={busy}
          >
            Add half day
          </button>
        </div>
      )}
    </div>
  );
}
