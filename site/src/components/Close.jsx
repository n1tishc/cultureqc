import { CONTACT, DEMO_VIDEO, REPO_URL } from "../config";
import { GENESIS } from "../lib/hash";

export default function Close({ leaves, onGo }) {
  const last = leaves[leaves.length - 1].record;

  return (
    <footer className="close" id="sec-close">
      <p className="closehook rv">
        A call you can act on, and <em>prove you were right to.</em>
      </p>

      <div className="actions rv" id="close-actions">
        {/* Until there is a recording to link, the primary action is the thing
            that actually exists: the analysis view. */}
        <a
          className="cta"
          href={DEMO_VIDEO || "#/analysis"}
          {...(DEMO_VIDEO
            ? { target: "_blank", rel: "noopener" }
            : {
                onClick: (e) => {
                  e.preventDefault();
                  onGo("analysis");
                },
              })}
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <path d="M6 4l14 8-14 8V4z" strokeLinejoin="round" />
          </svg>
          See it run
        </a>

        {/* An unanswered address is marked pending, not silently dropped: a
            missing entry on a document is a visible blank, never an absence. */}
        {!REPO_URL && (
          <span className="cta2 pending" aria-disabled="true">
            Source &mdash; address not yet issued
          </span>
        )}
        {REPO_URL && (
          <a className="cta2" href={REPO_URL} target="_blank" rel="noopener">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              aria-hidden="true"
            >
              <path
                d="M9 19c-4 1.3-4-2.2-5.6-2.7M15 21v-3.3a2.9 2.9 0 0 0-.8-2.2c2.7-.3 5.5-1.3 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.3 4.3 0 0 0-.1-3.2s-1-.3-3.3 1.2a11.4 11.4 0 0 0-6 0C6.7 2.8 5.7 3.1 5.7 3.1a4.3 4.3 0 0 0-.1 3.2A4.6 4.6 0 0 0 4.3 9.5c0 4.7 2.8 5.7 5.5 6a2.9 2.9 0 0 0-.8 2.2V21"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Source
          </a>
        )}

        {!CONTACT && (
          <span className="cta2 pending" aria-disabled="true">
            Contact &mdash; address not yet issued
          </span>
        )}
        {CONTACT && (
          <a className="cta2" href={"mailto:" + CONTACT}>
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              aria-hidden="true"
            >
              <rect x="3" y="5" width="18" height="14" rx="1" />
              <path
                d="M3.4 6l8.6 6.6L20.6 6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Get in touch
          </a>
        )}
      </div>

      <div className="colophon rv">
        <div>
          <h3>Built by</h3>
          <p id="author-block">
            Nitish C. cultureQC is an independent build: the segmentation and QC
            pipeline, the rules engine, the hash-chained record layer, the review
            console and this page.
          </p>
        </div>
        <div>
          <h3>Stack</h3>
          <p>
            Cellpose-SAM &middot; EfficientNet-B0 &middot; Grad-CAM &middot;
            Python &middot; SHA-256 hash-chained JSONL
          </p>
        </div>
        <div>
          <h3>Status</h3>
          <p>
            Working pipeline with a review console and a verified audit chain.
            Not a cleared medical device and not a validated GMP system; the
            record schema is designed to map onto one.
          </p>
        </div>
      </div>

      <p className="seal" id="seal">
        <b>Terminal record hash</b> &nbsp;{last.record_hash}
        <br />
        <b>Chain</b> &nbsp;{leaves.length} records &middot; genesis{" "}
        {GENESIS.slice(0, 16)}… &middot; schema {last.schema_version}
      </p>
    </footer>
  );
}
