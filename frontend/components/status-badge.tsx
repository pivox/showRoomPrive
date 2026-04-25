"use client";

import { cn } from "@/lib/utils";

const configs: Record<string, { label: string; className: string }> = {
  idle:    { label: "Inactif",    className: "bg-gray-100 text-gray-600" },
  running: { label: "En cours",   className: "bg-orange-100 text-orange-700" },
  pending: { label: "En attente", className: "bg-yellow-100 text-yellow-700" },
  done:    { label: "Terminé",    className: "bg-green-100 text-green-700" },
  error:   { label: "Erreur",     className: "bg-red-100 text-red-700" },
  active:  { label: "Actif",      className: "bg-green-100 text-green-700" },
  stopped: { label: "Stoppé",     className: "bg-gray-100 text-gray-600" },
};

interface Props {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: Props) {
  const cfg = configs[status] ?? { label: status, className: "bg-gray-100 text-gray-500" };
  return (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", cfg.className, className)}>
      {cfg.label}
    </span>
  );
}
