"use client";

import { Moon, Sun } from "lucide-react";

import { useTheme } from "@/components/theme-provider";

export function ThemeToggle({ variant = "surface" }: { variant?: "surface" | "entry" }) {
  const { theme, setTheme } = useTheme();
  const isDark = theme === "dark";
  const nextTheme = isDark ? "light" : "dark";

  return (
    <button
      aria-checked={isDark}
      aria-label={`Switch to ${nextTheme} theme`}
      className={`theme-toggle theme-toggle-${variant}`}
      onClick={() => setTheme(nextTheme)}
      role="switch"
      title={`Switch to ${nextTheme} theme`}
      type="button"
    >
      {isDark ? <Moon className="h-4 w-4" aria-hidden="true" /> : <Sun className="h-4 w-4" aria-hidden="true" />}
    </button>
  );
}
