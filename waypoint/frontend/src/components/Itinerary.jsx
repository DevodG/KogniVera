import { formatMoney, formatSignedMoney, money } from "../money.js";

const SLOT_LABEL = {
  morning: "Morning",
  afternoon: "Afternoon",
  evening: "Evening",
  overnight: "Overnight",
};

/**
 * The package workspace: day-by-day itinerary with swappable, optional and
 * included components, plus live server-side repricing.
 */
export default function Itinerary({ itinerary, onSwap, busy }) {
  if (!itinerary) return null;
  return (
    <div className="card">
      <h2 className="card__title">
        Itinerary workspace
        <span className="badge badge--source">PackagePro.package_components</span>
      </h2>
      <p className="card__sub">
        Swap an activity for a verified alternative from the same package and{" "}
        <code>swap_group</code>. The server reprices every change; the browser never totals.
      </p>

      {itinerary.days.map((day) => (
        <div className="day" key={day.day_index}>
          <div className="day__head">
            DAY {day.day_index} / {itinerary.days.length}
            {day.date ? ` · ${day.date}` : ""}
          </div>
          {day.components.map((comp) => (
            <div className="comp" key={comp.component_id}>
              <span className="comp__slot">{SLOT_LABEL[comp.slot] || comp.slot}</span>
              <div className="comp__body">
                <p className="comp__title">
                  {comp.title}{" "}
                  {comp.is_optional ? (
                    <span className="badge badge--optional">optional</span>
                  ) : (
                    <span className="badge badge--included">included</span>
                  )}{" "}
                  {comp.is_swappable ? (
                    <span className="badge badge--swappable">swappable</span>
                  ) : null}
                </p>
                <p className="comp__type">
                  {comp.component_type}
                  {comp.entity_id ? ` · ${comp.entity_id}` : ""}
                </p>
              </div>
              <div className="comp__price">
                {comp.is_optional ? "+" : ""}
                {formatMoney(comp.price_delta, comp.currency)}
                <small>{comp.is_optional ? "optional add-on" : "in package"}</small>
              </div>
              <ComponentActions
                comp={comp}
                alternatives={alternativesFor(itinerary, comp)}
                onSwap={onSwap}
                onRemove={onRemove}
                onRestore={onRestore}
                busy={busy}
              />
            </div>
          ))}
        </div>
      ))}

    </div>
  );
}

function alternativesFor(itinerary, comp) {
  if (!comp.is_swappable || !comp.swap_group) return [];
  const group = itinerary.components.filter(
    (c) => c.swap_group === comp.swap_group && c.component_id !== comp.component_id,
  );
  return group;
}

function ComponentActions({ comp, alternatives, onSwap, busy }) {
  if (!alternatives.length) {
    if (comp.is_optional) {
      return (
        <span className="tiny muted" style={{ minWidth: 86 }}>
          optional add-on
        </span>
      );
    }
    return (
      <span className="tiny muted" style={{ minWidth: 86 }}>
        fixed
      </span>
    );
  }
  if (!alternatives.length) {
    return (
      <span className="tiny muted" style={{ minWidth: 86 }}>
        no alternative
      </span>
    );
  }
  return (
    <div className="row" style={{ gap: 6 }}>
      {alternatives.map((alt) => (
        <button
          key={alt.component_id}
          className="btn tiny"
          onClick={() => onSwap && onSwap(comp.component_id, alt.component_id)}
          disabled={busy}
          title={`Swap to ${alt.title}`}
        >
          swap → {alt.title.length > 22 ? `${alt.title.slice(0, 22)}…` : alt.title}
          <span style={{ color: "var(--amber)" }}>
            {" "}
            {formatSignedMoney(
              money(alt.price_delta).minus(money(comp.price_delta)).toString(),
              comp.currency,
            )}
          </span>
        </button>
      ))}
    </div>
  );
}
