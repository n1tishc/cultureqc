import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import DATA from "./data.json";
import Home from "./pages/Home";
import ValidationPage from "./pages/ValidationPage";
import ReleaseNotesPage from "./pages/ReleaseNotesPage";

/* One bundle, three pages: each HTML entry names its page on <body>. */
const PAGES = { home: Home, validation: ValidationPage, "release-notes": ReleaseNotesPage };
const Page = PAGES[document.body.dataset.page] || Home;

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <Page data={DATA} />
  </StrictMode>,
);
