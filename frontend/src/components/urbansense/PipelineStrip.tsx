import { Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export const pipelineSteps = [
  "Video received",
  "Frames read",
  "Potholes found",
  "Placed on map",
];

export function PipelineStrip({ step }: { step: number }) {
  return (
    <ol className="grid grid-cols-4 gap-2">
      {pipelineSteps.map((label, idx) => {
        const done = step > idx;
        const active = step === idx;
        return (
          <li key={label} className="min-w-0">
            <span
              className={cn(
                "block h-1 rounded-full",
                done ? "bg-primary" : active ? "bg-primary/50" : "bg-border",
              )}
            />
            <span className="mt-2 flex items-center gap-1 text-[11px] leading-tight text-muted-foreground">
              {done ? (
                <Check className="size-3 shrink-0 text-primary" />
              ) : active ? (
                <Loader2 className="size-3 shrink-0 animate-spin text-primary" />
              ) : null}
              <span className="truncate">{label}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
