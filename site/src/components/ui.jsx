/* Shared marks. Icons are drawn here in one 1.6px stroke on a 16px grid, so
   every glyph on the page comes from the same hand. */

const P = {
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round",
  strokeLinejoin: "round",
};

export function Icon({ name }) {
  const common = { viewBox: "0 0 16 16", width: "1em", height: "1em", "aria-hidden": true, focusable: "false", className: "ico" };
  switch (name) {
    case "external":
      return <svg {...common}><path {...P} d="M6 3.5H3.5v9h9V10M9 3h4v4M13 3L7.5 8.5" /></svg>;
    case "down":
      return <svg {...common}><path {...P} d="M8 3v10M4 9l4 4 4-4" /></svg>;
    case "check":
      return <svg {...common}><circle {...P} cx="8" cy="8" r="6.2" /><path {...P} d="M5.3 8.2l1.9 1.9 3.6-4" /></svg>;
    case "cross":
      return <svg {...common}><rect {...P} x="2" y="2" width="12" height="12" rx="1.5" /><path {...P} d="M5.5 5.5l5 5M10.5 5.5l-5 5" /></svg>;
    case "mixed":
      return <svg {...common}><path {...P} d="M8 2l6.5 11.5h-13z" /><path {...P} d="M8 6.5v3.2M8 11.6v.1" /></svg>;
    case "none":
      return <svg {...common}><circle {...P} cx="8" cy="8" r="6.2" strokeDasharray="2.2 2.2" /></svg>;
    case "info":
      return <svg {...common}><circle {...P} cx="8" cy="8" r="6.2" /><path {...P} d="M8 7.3v4M8 4.8v.1" /></svg>;
    case "flag":
      return <svg {...common}><path {...P} d="M8 1.8l6.2 6.2L8 14.2 1.8 8z" /><path {...P} d="M8 5.5v3M8 10.4v.1" /></svg>;
    case "clear":
      return <svg {...common}><path {...P} d="M8 1.8l6.2 6.2L8 14.2 1.8 8z" /></svg>;
    case "passage":
      return <svg {...common}><path {...P} d="M3 8h9M8.5 4.5L12 8l-3.5 3.5" /></svg>;
    case "hold":
      return <svg {...common}><path {...P} d="M5.5 3.5v9M10.5 3.5v9" /></svg>;
    case "human_review":
      return <svg {...common}><circle {...P} cx="8" cy="5.6" r="2.6" /><path {...P} d="M3 13.6c.8-2.6 2.7-3.8 5-3.8s4.2 1.2 5 3.8" /></svg>;
    case "reimage":
      return <svg {...common}><path {...P} d="M2.5 5.5V3h2.5M13.5 10.5V13H11M3 9.5a5 5 0 0 0 9.4 1.8M13 6.5A5 5 0 0 0 3.6 4.7" /></svg>;
    case "feed":
      return <svg {...common}><path {...P} d="M8 2.5c2.5 3 3.8 5 3.8 7a3.8 3.8 0 0 1-7.6 0c0-2 1.3-4 3.8-7z" /></svg>;
    default:
      return null;
  }
}

const ACTION_WORD = {
  passage: "Passage",
  feed: "Feed",
  hold: "Hold",
  human_review: "Human review",
  reimage: "Re-image",
};

export function Action({ a }) {
  return (
    <span className="action" data-a={a}>
      <Icon name={a} />
      {ACTION_WORD[a] || a}
    </span>
  );
}

export const actionWord = (a) => ACTION_WORD[a] || a;

const VERDICT_ICON = { pass: "check", fail: "cross", mixed: "mixed", none: "none", info: "info", untested: "none" };

export function Verdict({ k, children }) {
  return (
    <span className="verdict" data-k={k}>
      <Icon name={VERDICT_ICON[k] || "info"} />
      {children}
    </span>
  );
}

export function Section({ id, title, children, lede, sources }) {
  return (
    <section className="sec" id={id} aria-labelledby={`${id}-h`}>
      <div className="wrap">
        <header className="sec-head">
          <h2 id={`${id}-h`}>{title}</h2>
          <div>
            {lede}
            {sources ? <p className="sources">{sources}</p> : null}
          </div>
        </header>
        {children}
      </div>
    </section>
  );
}

export function Fig({ letter, title, children, legend, className = "" }) {
  return (
    <figure className={`fig ${className}`} style={{ margin: 0 }}>
      <div className="fig-head">
        {letter ? <span className="letter">{letter}</span> : null}
        <h3>{title}</h3>
      </div>
      {children}
      {legend ? <figcaption className="legend">{legend}</figcaption> : null}
    </figure>
  );
}

export const pct = (x, d = 1) => `${Number(x).toFixed(d)}%`;
export const short = (h, n = 6) => `${h.slice(0, n)}…${h.slice(-4)}`;
