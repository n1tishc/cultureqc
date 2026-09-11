import { CONTACT, REPO_URL } from "../config";

function repoLink(path, label) {
  return REPO_URL ? (
    <a href={`${REPO_URL}/blob/main/${path}`} target="_blank" rel="noopener">
      {label}
    </a>
  ) : (
    <code>{path}</code>
  );
}

export default function EngineeringNotes() {
  return (
    <section className="sec" id="sec-notes">
      <div className="sechead rv">
        <h1>Engineering notes</h1>
        <span className="docaddr">About &middot; harness</span>
      </div>
      <p className="lede rv">
        What this build is, who built it, and how the pipeline behind it is
        tested and reproduced.
      </p>

      <div className="colophon rv">
        <div>
          <h3>Built by</h3>
          <p>
            Nitish C. cultureQC is an independent build: the segmentation and
            QC pipeline, the rules engine, the hash-chained record layer, this
            review console, and the site itself.
          </p>
        </div>
        <div>
          <h3>Stack</h3>
          <p>
            Cellpose-SAM &middot; EfficientNet-B0 &middot; Grad-CAM &middot;
            Python &middot; SHA-256 hash-chained JSONL &middot; React
          </p>
        </div>
        <div>
          <h3>Status</h3>
          <p>
            Working pipeline with a review console and a verified audit
            chain. Not a cleared medical device and not a validated GMP
            system; the record schema is designed to map onto one — see the
            trail mapping below.
          </p>
        </div>
      </div>

      <h2>Test suite</h2>
      <ul className="notes-list">
        <li>
          <strong>API contract</strong> —{" "}
          {repoLink("deploy/hf-space/test_api.py", "deploy/hf-space/test_api.py")}
          , run with <code>pytest</code> against a stubbed model so it exercises
          the request/response contract without needing torch or Cellpose
          installed.
        </li>
        <li>
          <strong>Stream parser</strong> —{" "}
          {repoLink(
            "site/tests/analysisStream.test.js",
            "site/tests/analysisStream.test.js",
          )}
          , run with Node&rsquo;s built-in test runner. Covers NDJSON split
          across arbitrary chunk boundaries, dropped connections, and
          heartbeat filtering.
        </li>
      </ul>

      <h2>Continuous integration</h2>
      <p>
        {repoLink(".github/workflows/tests.yml", "Two CI jobs")} run on every
        push and pull request:
      </p>
      <ul className="notes-list">
        <li>
          <strong>API contract</strong> — installs a torch/Cellpose-free
          dependency set, runs the pytest contract suite, then checks that{" "}
          {repoLink("deploy/hf-space", "deploy/hf-space")} is byte-identical to
          the pipeline code it packages, so the deployed Space cannot silently
          drift from this repository.
        </li>
        <li>
          <strong>Site build</strong> — installs Node dependencies, runs the
          stream-parser tests, builds the production bundle, then regenerates{" "}
          <code>site/src/data.json</code> from the committed pipeline output
          and fails the build if it differs — the reference data this page
          shows is always exactly what the pipeline produced, never
          hand-edited.
        </li>
      </ul>

      <h2>Training data &amp; evaluation</h2>
      <p>
        Nothing under <code>data/</code> is tracked; it is all downloaded or
        derived and reproducible from two scripts — see{" "}
        {repoLink("docs/DATA.md", "docs/DATA.md")} for the full provenance
        table. The QC classifier trains on real phase-contrast microscopy
        (DeepBacs, Zenodo record 5550935) with bacterial sprites, turbidity,
        detachment, and image artifacts composited in via{" "}
        {repoLink(
          "scripts/synth_contamination.py",
          "scripts/synth_contamination.py",
        )}
        . Per-cell-line thresholds live under{" "}
        {repoLink("config/lines", "config/lines/")}.
      </p>

      <h2>Record schema</h2>
      <p>
        Every analysed image is written against one JSON Schema —{" "}
        {repoLink("culture/schema.json", "culture/schema.json")} — and{" "}
        {repoLink("docs/audit_mapping.md", "docs/audit_mapping.md")} maps each
        field to the 21 CFR Part 11 §11.10 clause it is designed to satisfy.
        That mapping is a pattern demonstration, not a compliance claim: real
        GMP validation needs formal IQ/OQ/PQ and organisational SOPs beyond the
        scope of this project.
      </p>

      {!REPO_URL && (
        <p className="foot">
          The source repository is not public yet, so the paths above are
          shown as references rather than links. This page summarises what
          they contain directly.
        </p>
      )}

      {CONTACT && (
        <p className="foot">
          Questions about any of this — <a href={"mailto:" + CONTACT}>get in touch</a>.
        </p>
      )}
    </section>
  );
}
