"use client";

import { cn } from "@/lib/utils";

interface Props {
  value: number | null;
  className?: string;
}

export function ConfidenceBar({ value, className }: Props) {
  if (value == null) return <span className="text-gray-400">—</span>;
  const pct = Math.min(100, Math.max(0, value));
  const color = pct >= 70 ? "bg-green-500" : pct >= 40 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="h-2 w-24 rounded-full bg-gray-200">
        <div className={cn("h-2 rounded-full", color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-600">{pct}%</span>
    </div>
  );
}
