import { cn } from "@/lib/utils";
import { statusLabel, type Incident } from "@/lib/types";

export function StatusTag({ incident }: { incident: Incident }) {
  const tone =
    incident.status === "verified"
      ? "bg-verified/15 text-verified"
      : incident.status === "review"
        ? "bg-review/15 text-review"
        : "bg-muted text-muted-foreground";
  return (
    <span className={cn("inline-flex rounded-full px-2.5 py-1 text-xs font-medium", tone)}>
      {statusLabel[incident.status]}
    </span>
  );
}
