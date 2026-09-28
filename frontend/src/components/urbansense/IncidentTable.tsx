import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { StatusTag } from "./StatusTag";
import type { Incident } from "@/lib/types";

type SortKey = "id" | "road" | "confidence" | "sightings" | "status" | "lastSeen";

const columns: { key: SortKey; label: string; className?: string }[] = [
  { key: "id", label: "ID" },
  { key: "road", label: "Road" },
  { key: "confidence", label: "Confidence" },
  { key: "sightings", label: "Sightings" },
  { key: "status", label: "Status" },
  { key: "lastSeen", label: "Last seen" },
];

export function IncidentTable({
  incidents,
  selectedId,
  onSelect,
}: {
  incidents: Incident[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<{ key: SortKey; dir: 1 | -1 }>({ key: "lastSeen", dir: -1 });

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = incidents.filter(
      (i) => !q || i.id.toLowerCase().includes(q) || i.road.toLowerCase().includes(q),
    );
    return [...filtered].sort((a, b) => {
      const av = a[sort.key];
      const bv = b[sort.key];
      if (typeof av === "number" && typeof bv === "number") return (av - bv) * sort.dir;
      return String(av).localeCompare(String(bv)) * sort.dir;
    });
  }, [incidents, query, sort]);

  return (
    <section className="rounded-2xl border border-border bg-card p-4 sm:p-6">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="mr-auto text-xl font-semibold">Incident log</h2>
        <div className="relative w-full sm:w-72">
          <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by ID or road"
            aria-label="Search incidents"
            className="rounded-xl pl-9"
          />
        </div>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs text-muted-foreground">
              {columns.map((c) => (
                <th key={c.key} className="py-2 pr-4 font-medium">
                  <button
                    className="inline-flex items-center gap-1 hover:text-foreground"
                    onClick={() =>
                      setSort((s) =>
                        s.key === c.key
                          ? { key: c.key, dir: s.dir === 1 ? -1 : 1 }
                          : { key: c.key, dir: 1 },
                      )
                    }
                  >
                    {c.label}
                    {sort.key === c.key &&
                      (sort.dir === 1 ? (
                        <ArrowUp className="size-3" />
                      ) : (
                        <ArrowDown className="size-3" />
                      ))}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((i) => (
              <tr
                key={i.id}
                tabIndex={0}
                role="button"
                aria-label={`Select ${i.id} on ${i.road}`}
                onClick={() => onSelect(i.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelect(i.id);
                  }
                }}
                className={cn(
                  "cursor-pointer border-b border-border/60 transition-colors hover:bg-accent/40",
                  selectedId === i.id && "bg-accent/60",
                )}
              >
                <td className="py-3 pr-4 font-mono text-xs">{i.id}</td>
                <td className="py-3 pr-4">{i.road}</td>
                <td className="py-3 pr-4">
                  <div className="flex items-center gap-2">
                    <span className="h-1.5 w-20 rounded-full bg-muted">
                      <span
                        className="block h-1.5 rounded-full bg-primary"
                        style={{ width: `${Math.round(i.confidence * 100)}%` }}
                      />
                    </span>
                    <span className="tabular-nums">{Math.round(i.confidence * 100)}%</span>
                  </div>
                </td>
                <td className="py-3 pr-4 tabular-nums">{i.sightings}</td>
                <td className="py-3 pr-4">
                  <StatusTag incident={i} />
                </td>
                <td className="py-3 pr-4 text-xs text-muted-foreground">
                  {new Date(i.lastSeen).toLocaleDateString("en-IN", {
                    day: "2-digit",
                    month: "short",
                  })}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && (
          <p className="py-10 text-center text-sm text-muted-foreground">
            No incidents match. Clear the search or pick another filter.
          </p>
        )}
      </div>
    </section>
  );
}
