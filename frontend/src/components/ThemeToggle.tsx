import { Moon, Sun } from "lucide-react";
import { useStore } from "../store";

export function ThemeToggle() {
  const { theme, setTheme } = useStore();

  return (
    <button
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      className="p-2 rounded-lg hover:bg-elevated text-muted hover:text-foreground transition-colors"
      title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
    >
      {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
    </button>
  );
}
