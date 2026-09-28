import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import type { FilterKey } from "@/lib/types";

function useCountUp(target: number) {
  const [value, setValue] = useState(0);
  const raf = useRef<number | null>(null);
  useEffect(() => {
    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setValue(target);
      return;
    }
    const start = performance.now();
    const from = 0;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / 700);
      setValue(Math.round(from + (target - from) * (1 - Math.pow(1 - t, 3))));
      if (t < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
    };
  }, [target]);
  return value;
}

function StatCard({
  label,
  value,
  active,
  tone,
  onClick,
}: {
  label: string;
  value: number;
  active: boolean;
  tone: string;
  onClick: () => void;
}) {
  const shown = useCountUp(value);
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "rounded-2xl border bg-card p-4 text-left transition-colors hover:bg-accent/40",
        active ? "border-primary" : "border-border",
      )}
    >
      <span className={cn("mb-2 block h-1 w-8 rounded-full", tone)} />
      <p className="font-display text-3xl font-semibold tabular-nums">{shown}</p>
      <p className="mt-1 text-xs leading-snug text-muted-foreground">{label}</p>
    </button>
  );
}

export function StatCards({
  counts,
  filter,
  onFilter,
}: {
  counts: { all: number; verified: number; review: number; high: number };
  filter: FilterKey;
  onFilter: (f: FilterKey) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-3">
      <StatCard
        label="Incidents reported"
        value={counts.all}
        tone="bg-primary"
        active={filter === "all"}
        onClick={() => onFilter("all")}
      />
      <StatCard
        label="Confirmed by multiple sightings"
        value={counts.verified}
        tone="bg-verified"
        active={filter === "verified"}
        onClick={() => onFilter("verified")}
      />
      <StatCard
        label="Waiting for review"
        value={counts.review}
        tone="bg-review"
        active={filter === "review"}
        onClick={() => onFilter("review")}
      />
      <StatCard
        label="High priority, 90%+ confidence"
        value={counts.high}
        tone="bg-hazard"
        active={filter === "high"}
        onClick={() => onFilter("high")}
      />
    </div>
  );
}
