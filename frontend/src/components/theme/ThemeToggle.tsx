"use client";

import { useEffect, useState } from "react";
import { Sun, Moon } from "lucide-react";
import { cn } from "@/lib/utils";

const STORAGE_KEY = "mto-theme";

function applyTheme(theme: "light" | "dark") {
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark" | null>(null);

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    const initial = stored === "dark" || stored === "light" ? stored : "light";
    setTheme(initial);
  }, []);

  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    applyTheme(next);
    window.localStorage.setItem(STORAGE_KEY, next);
  };

  // Avoid rendering a possibly-wrong icon before we've read localStorage.
  if (theme === null) {
    return <div className="h-9 w-[92px]" aria-hidden="true" />;
  }

  return (
    <button
      onClick={toggle}
      aria-label={theme === "dark" ? "Switch to vellum (light) mode" : "Switch to blueprint (dark) mode"}
      className={cn(
        "flex h-9 items-center gap-2 rounded-sm border px-3 text-xs font-mono uppercase tracking-widest transition-colors",
        "border-graphite-700/25 text-graphite-700 hover:bg-graphite-700/5",
        "dark:border-linework/25 dark:text-linework dark:hover:bg-linework/10"
      )}
    >
      {theme === "dark" ? <Moon className="h-3.5 w-3.5" /> : <Sun className="h-3.5 w-3.5" />}
      {theme === "dark" ? "Blueprint" : "Vellum"}
    </button>
  );
}
