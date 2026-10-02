import { Fig, Path, Section, Verdict } from "./ui";

/* The confluency calibration profiles study (results/confluency_profiles.md,
   pre-registered): one cutoff and one 90% error band per imaging setup, each
   tested on held-out labelled images from its own setup. Every number comes
   from data.profiles, which build_data.py copies from
   results/confluency_profiles.json. */

const STUDY = {
  validated: ["pass", "Validated"],
  failed: ["fail", "Failed its criteria"],
  in_domain_check: ["none", "In-domain check only"],
};

const fx = (x, d = 2) => (x === null || x === undefined ? "—" : Number(x).toFixed(d));
const cut = (x) => (x >= 0 ? `+${x.toFixed(1)}` : `−${Math.abs(x).toFixed(1)}`);

export function ProfileErrorFigure({ data, letter = "A" }) {
  const P = data.profiles;
  const max = Math.ceil(Math.max(...P.items.flatMap((p) => [p.shipped.mae, p.profile.mae])) / 5) * 5;
  return (
    <Fig
      letter={letter}
      title="Error against expert masks, per imaging setup"
      legend={
        <>
          Mean absolute error in percentage points on each setup’s held-out test images: grey at Cellpose’s default cutoff, ink at the cutoff calibrated on that setup’s own labelled images. Source: <Path>{P.source}</Path>.
        </>
      }
    >
      <div className="bars prof-bars">
        {P.items.map((p) => (
          <div key={p.id} className="prof-row">
            <span className="prof-name">
              {p.label}
              <span className="verdict-note">
                n = {p.n_test} test images · {p.study.split(";")[0]}
              </span>
            </span>
            <div className="prof-pair">
              {[
                ["default", p.shipped.mae, "var(--rule-2)"],
                ["calibrated", p.profile.mae, "var(--cell-ink)"],
              ].map(([k, v, c]) => (
                <div className="bars-row" key={k}>
                  <span>{k === "default" ? "default cutoff" : `calibrated ${cut(p.cutoff)}`}</span>
                  <span className="track">
                    <i style={{ width: `${(v / max) * 100}%`, background: c, opacity: 1 }} />
                  </span>
                  <span className="v">{fx(v)} pp</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </Fig>
  );
}

export function TransferTable({ data }) {
  const P = data.profiles;
  const cols = P.items.map((p) => p.id);
  return (
    <div className="table-wrap" tabIndex={0} role="region" aria-label="Test error under each setup's cutoff">
      <table>
        <thead>
          <tr>
            <th scope="col">Test images ↓ · cutoff from →</th>
            {P.items.map((p) => (
              <th scope="col" key={p.id}>
                {p.id} ({cut(p.cutoff)})
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {P.items.map((row) => (
            <tr key={row.id}>
              <td>{row.label}</td>
              {cols.map((c) => (
                <td key={c} className={c === row.id ? "num own" : "num"}>
                  {fx(row.transfer[c])} pp
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function AcceptanceTable({ data }) {
  const P = data.profiles;
  const crit = [
    ["A1", "MAE ≤ 5 pp"],
    ["A2", "MAE ≤ 5 pp at 60–90%"],
    ["A3", "|bias| ≤ 3 pp at 60–90%"],
    ["A4", "Passage call ≥ 95% right at 80%"],
    ["A5", "90% band covers ≥ 85%"],
  ];
  const kind = (v) => (v === "pass" ? "pass" : v === "fail" ? "fail" : "none");
  return (
    <div className="table-wrap" tabIndex={0} role="region" aria-label="Pre-registered acceptance criteria per profile">
      <table>
        <thead>
          <tr>
            <th scope="col">Profile</th>
            {crit.map(([k, t]) => (
              <th scope="col" key={k}>
                <span className="vid">{k}</span>
                {t}
              </th>
            ))}
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {P.items.map((p) => (
            <tr key={p.id}>
              <td>
                {p.label}
                <span className="verdict-note">
                  cutoff {cut(p.cutoff)}, band ±{fx(p.band_pp, 1)} pp; {p.n_calib} calibration / {p.n_test} test images
                </span>
              </td>
              {crit.map(([k]) => (
                <td key={k}>
                  <Verdict k={kind(p.acceptance[k].verdict)}>{p.acceptance[k].verdict}</Verdict>
                  <span className="verdict-note">{p.acceptance[k].detail}</span>
                </td>
              ))}
              <td>
                <Verdict k={(STUDY[p.status] || ["none"])[0]}>{(STUDY[p.status] || ["none", p.status])[1]}</Verdict>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Profiles({ data }) {
  const P = data.profiles;
  if (!P) return null;
  return (
    <Section
      id="profiles"
      title="Confluency calibrated per imaging setup"
      lede={
        <>
          <p>
            The cutoff that turns Cellpose-SAM’s probability map into a number depends on the microscope. Each setup gets a calibration profile: a cutoff fitted on labelled images from that setup, and a 90% error band measured on images left out of the fit. Every reading names its profile, and a reading whose band includes the passage target goes to a person. Method, splits and pass criteria were committed before any image was scored.
          </p>
          <p className="sources">
            <Path>{P.source}</Path>
          </p>
        </>
      }
    >
      <div className="figs g2">
        <ProfileErrorFigure data={data} />
        <Fig letter="B" title="Why one cutoff per setup" legend={<>Test error on each setup (rows) with the cutoff calibrated on each setup (columns); the diagonal is the setup’s own profile.</>}>
          <TransferTable data={data} />
        </Fig>
      </div>
      <h3 className="sub-h">Pre-registered acceptance, on held-out images</h3>
      <AcceptanceTable data={data} />
    </Section>
  );
}
