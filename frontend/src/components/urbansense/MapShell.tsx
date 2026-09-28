import { Suspense, lazy, useEffect, useState } from "react";
import type { Incident } from "@/lib/types";

const IncidentMap = lazy(() => import("./IncidentMap"));

export function MapShell(props: {
  incidents: Incident[];
  selectedId: string | null;
  newId: string | null;
  onSelect: (id: string) => void;
}) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  if (!mounted) return <div className="h-full w-full bg-muted" />;

  return (
    <Suspense fallback={<div className="h-full w-full bg-muted" />}>
      <IncidentMap {...props} />
    </Suspense>
  );
}
