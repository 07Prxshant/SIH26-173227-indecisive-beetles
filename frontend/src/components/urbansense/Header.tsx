import { Moon, Sun } from "lucide-react";

export function Header({ theme, onToggleTheme }: { theme: "dark" | "light"; onToggleTheme: () => void }) {
  return (
    <header className="sticky top-0 z-[500] border-b border-border bg-background/85 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-3 sm:px-6">
        <div className="flex size-9 items-center justify-center rounded-xl bg-foreground/90">
          <span className="lane-mark block h-1 w-5 rounded-full" />
        </div>
        <div className="mr-auto">
          <p className="font-display text-lg leading-none font-semibold">MIRA</p>
          <p className="text-xs text-muted-foreground">Mobile Intelligence for Road Analytics</p>
        </div>
        <span className="hidden items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground sm:inline-flex">
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-2 animate-ping rounded-full bg-verified opacity-75" />
            <span className="relative inline-flex size-2 rounded-full bg-verified" />
          </span>
          System operational
        </span>
        <button
          onClick={onToggleTheme}
          aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          className="inline-flex size-9 items-center justify-center rounded-xl border border-border bg-card text-foreground transition-colors hover:bg-accent"
        >
          {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
        </button>
      </div>
    </header>
  );
}
