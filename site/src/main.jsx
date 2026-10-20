import { StrictMode, useEffect } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import DATA from "./data.json";
import Home from "./pages/Home";
import RecordsPage from "./pages/RecordsPage";
import ValidationPage from "./pages/ValidationPage";
import ReleaseNotesPage from "./pages/ReleaseNotesPage";

/* One bundle, four pages: each HTML entry names its page on <body>. */
const PAGES = { home: Home, records: RecordsPage, validation: ValidationPage, "release-notes": ReleaseNotesPage };
const Page = PAGES[document.body.dataset.page] || Home;

/* The page is drawn after the browser has looked for the URL's #fragment and found nothing, so a link such as
   /records?record=…#chain opened at the top. Go to it once the page is drawn, unless the page itself (Home's
   appendix links) or the reader has already scrolled. Rendered after <Page>, so its effects run first. */
function FollowHash() {
  useEffect(() => {
    requestAnimationFrame(() => {
      const target = window.location.hash.length > 1 && document.getElementById(window.location.hash.slice(1));
      if (target && window.scrollY === 0) target.scrollIntoView({ behavior: "instant" });
    });
  }, []);
  return null;
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <Page data={DATA} />
    <FollowHash />
  </StrictMode>,
);
