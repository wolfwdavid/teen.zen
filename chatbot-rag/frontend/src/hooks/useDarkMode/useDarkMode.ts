import { useEffect, useState } from "react";

const STORAGE_KEY = "app:theme"; // "light" | "dark"

export type Theme = "light" | "dark";

export function useDarkMode(): [Theme, (t?: Theme) => void] {
  const prefersDark = () =>
    typeof window !== "undefined" &&
    window.matchMedia &&
    window.matchMedia("(prefers-color-scheme: dark)").matches;

  const readInitial = (): Theme => {
    const saved = localStorage.getItem(STORAGE_KEY) as Theme | null;
    if (saved === "light" || saved === "dark") return saved;
    return prefersDark() ? "dark" : "light";
  };

  const [theme, setTheme] = useState<Theme>(readInitial);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, theme);
    // apply class to <html> so CSS vars take effect
    const root = document.documentElement;
    if (theme === "dark") root.classList.add("dark");
    else root.classList.remove("dark");
  }, [theme]);

  const toggle = (next?: Theme) => {
    if (next) setTheme(next);
    else setTheme((t) => (t === "dark" ? "light" : "dark"));
  };

  return [theme, toggle];
}
