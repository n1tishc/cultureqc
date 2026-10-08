import { useEffect, useState } from "react";
import { Icon } from "./ui";

/* What every page shares: the top bar, the closing call to action and the
   footer. The home page's sections are anchors; validation and release notes
   are pages of their own. */

/* eslint-disable-next-line no-undef */
export const COMMIT = typeof __COMMIT__ !== "undefined" ? __COMMIT__ : "";

/* The release the site describes; the release notes page lists what it holds. */
export const VERSION = "v0.4";

const HOME_NAV = [
  ["how", "How it works"],
  ["timeline", "Flask history"],
  ["records", "Records"],
  ["integration", "Integration"],
];

/* Home sections without a nav entry, observed so none of the links above
   stays lit while they are on screen. */
const UNLISTED = ["top", "accuracy", "specs", "scope"];

const PAGES = [
  ["validation", "/validation", "Validation"],
  ["release-notes", "/release-notes", "Release notes"],
];

const IDS = [...HOME_NAV.map(([id]) => id), ...UNLISTED];

function useActiveSection(ids, enabled) {
  const [active, setActive] = useState(null);
  useEffect(() => {
    if (!enabled) return undefined;
    const els = ids.map((id) => document.getElementById(id)).filter(Boolean);
    const io = new IntersectionObserver(
      (entries) => {
        const vis = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (vis[0]) setActive(vis[0].target.id);
      },
      { rootMargin: "-80px 0px -60% 0px" },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [ids, enabled]);
  return active;
}

export function TopBar({ data, page }) {
  const home = page === "home";
  const active = useActiveSection(IDS, home);
  return (
    <header className="bar">
      <div className="wrap bar-in">
        <a className="mark" href={home ? "#top" : "/"} aria-label="cultureQC, home">
          <Logo />
          <b>cultureQC</b>
          <span className="ver">{VERSION}</span>
        </a>
        <nav className="nav" aria-label="Site">
          {HOME_NAV.map(([id, label]) => (
            <a key={id} href={home ? `#${id}` : `/#${id}`} aria-current={home && active === id ? "true" : undefined}>
              {label}
            </a>
          ))}
          <span className="nav-sep" aria-hidden="true" />
          {PAGES.map(([key, href, label]) => (
            <a key={key} href={href} aria-current={page === key ? "page" : undefined}>
              {label}
            </a>
          ))}
        </nav>
        <a className="btn btn-primary" href={data.meta.console_url} target="_blank" rel="noreferrer">
          Live console <Icon name="external" />
        </a>
      </div>
    </header>
  );
}

/* A culture dish seen from above: the ring, and cells growing toward
   confluence. Drawn on the icon grid, in the ink and the model's cyan. */
export function Logo() {
  return (
    <svg className="logo" viewBox="0 0 20 20" width="20" height="20" aria-hidden="true" focusable="false">
      <circle cx="10" cy="10" r="8.6" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <path d="M5.2 11.6c1.2-.9 2.2-.7 3 .2.9 1 2 1.1 3 .2.9-.8 2-1 3.6-.2v2.4a6 6 0 0 1-9.6 0z" fill="var(--cell)" />
      <circle cx="7.6" cy="7.4" r="1.25" fill="var(--cell)" />
      <circle cx="11.6" cy="6.6" r="0.95" fill="var(--cell)" />
    </svg>
  );
}

export function CtaBand({ data }) {
  return (
    <section className="cta" aria-labelledby="cta-h">
      <div className="wrap cta-in">
        <div>
          <h2 id="cta-h">Run it on your own image</h2>
          <p>The console runs the same code as everything on this site, on any phase-contrast image you give it, and shows the reading, the anomaly check, the action and the record.</p>
        </div>
        <div className="cta-actions">
          <a className="btn btn-light" href={data.meta.console_url} target="_blank" rel="noreferrer">
            Open the live console <Icon name="external" />
          </a>
          <a className="btn btn-ghost-dark" href={data.meta.repo_url} target="_blank" rel="noreferrer">
            Read the source <Icon name="external" />
          </a>
        </div>
      </div>
    </section>
  );
}

export function Footer({ data }) {
  const credits = [...new Set(data.examples.items.map((e) => e.credit))];
  return (
    <footer className="foot">
      <div className="wrap foot-grid">
        <div className="foot-brand">
          <a className="mark" href="/" aria-label="cultureQC, home">
            <Logo />
            <b>cultureQC</b>
            <span className="ver">{VERSION}</span>
          </a>
          <p>
            Every figure on this site is generated from the repository’s stored output by <code>site/assets/build_data.py</code>; the numbers come from the README tables that <code>tests/test_readme_provenance.py</code> checks against their source files.
          </p>
          <p className="foot-build">
            Built from <code>{data.meta.branch}</code>
            {COMMIT ? (
              <>
                {" "}
                at <code>{COMMIT.slice(0, 7)}</code>
              </>
            ) : null}
            .
          </p>
        </div>
        <div>
          <h4>Product</h4>
          <p>
            <a href="/#how">How it works</a>
          </p>
          <p>
            <a href="/#timeline">Flask history</a>
          </p>
          <p>
            <a href="/#records">Records</a>
          </p>
          <p>
            <a href="/#integration">Integration</a>
          </p>
        </div>
        <div>
          <h4>Evidence</h4>
          <p>
            <a href="/validation">Validation</a>
          </p>
          <p>
            <a href="/validation#detectability">What it can and cannot see</a>
          </p>
          <p>
            <a href="/release-notes">Release notes</a>
          </p>
        </div>
        <div>
          <h4>Resources</h4>
          <p>
            <a href={data.meta.console_url} target="_blank" rel="noreferrer">
              Live console <Icon name="external" />
            </a>
          </p>
          <p>
            <a href={data.meta.repo_url} target="_blank" rel="noreferrer">
              Source repository <Icon name="external" />
            </a>
          </p>
          <p>
            <a href="https://cultureqc.vercel.app" target="_blank" rel="noreferrer">
              The v0.2 site <Icon name="external" />
            </a>
          </p>
        </div>
      </div>
      <div className="wrap">
        <div className="foot-credits">
          <span>Images:</span>
          {credits.map((c) => (
            <span key={c}>{c}</span>
          ))}
        </div>
      </div>
    </footer>
  );
}

/* The header of a secondary page: a title, its lede and the page's own
   contents, so a long page is navigable from its top. */
export function PageHead({ title, lede, toc }) {
  return (
    <header className="page-head">
      <div className="wrap">
        <h1 id="top-h">{title}</h1>
        <div className="page-lede">{lede}</div>
        {toc ? (
          <nav className="toc" aria-label="On this page">
            {toc.map(([id, label]) => (
              <a key={id} href={`#${id}`}>
                {label}
              </a>
            ))}
          </nav>
        ) : null}
      </div>
    </header>
  );
}
