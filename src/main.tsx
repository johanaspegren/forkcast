import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import RecipeCollection from "./recipes/RecipeCollection";
import SwipeGame from "./swipe/SwipeGame";
import "./styles.css";

// Routed here rather than inside App so the recipe screen does not inherit the
// game's session hooks.
const path = window.location.pathname;

function Root() {
  if (path.startsWith("/recipes")) return <RecipeCollection />;
  if (path.startsWith("/swipe")) return <SwipeGame />;
  return <App />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root />
  </StrictMode>
);
