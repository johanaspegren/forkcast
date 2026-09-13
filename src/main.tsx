import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import RecipeCollection from "./recipes/RecipeCollection";
import "./styles.css";

// Routed here rather than inside App so the recipe screen does not inherit the
// game's session hooks.
const isRecipeRoute = window.location.pathname.startsWith("/recipes");

createRoot(document.getElementById("root")!).render(
  <StrictMode>{isRecipeRoute ? <RecipeCollection /> : <App />}</StrictMode>
);
