"use client";

import { Suspense, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { formatRelativeDate } from "@/lib/utils";
import { StatusBadge } from "@/components/status-badge";

function DashboardContent() {
  const qc = useQueryClient();
  const [confirmStop, setConfirmStop] = useState(false);

  const { data: scan } = useQuery({
    queryKey: ["scan-status"],
    queryFn: () => api.getScanStatus().then((r) => r.data),
    refetchInterval: (q) => (q.state.data?.status === "running" ? 2000 : 30000),
  });

  const { data: cron } = useQuery({
    queryKey: ["cron-status"],
    queryFn: () => api.getCronStatus().then((r) => r.data),
    refetchInterval: 30000,
  });

  const runScan = useMutation({
    mutationFn: () => api.runScan(),
    onSuccess: () => {
      toast.success("Scan lancé");
      qc.invalidateQueries({ queryKey: ["scan-status"] });
    },
    onError: (e: any) => {
      const msg = e?.response?.data?.detail ?? "Erreur lors du lancement";
      toast.error(msg);
    },
  });

  const startCron = useMutation({
    mutationFn: () => api.startCron(),
    onSuccess: () => {
      toast.success("Cron démarré");
      qc.invalidateQueries({ queryKey: ["cron-status"] });
    },
    onError: () => toast.error("Impossible de démarrer le cron"),
  });

  const stopCron = useMutation({
    mutationFn: () => api.stopCron(),
    onSuccess: () => {
      toast.success("Cron stoppé");
      setConfirmStop(false);
      qc.invalidateQueries({ queryKey: ["cron-status"] });
    },
    onError: () => toast.error("Impossible de stopper le cron"),
  });

  const scanning = scan?.status === "running";
  const cronActive = cron?.active ?? false;

  const nextRun = cron?.next_run_at
    ? new Date(cron.next_run_at).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })
    : null;
  const intervalMin = cron ? Math.round(cron.interval_seconds / 60) : null;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        {/* Scan card */}
        <div className="rounded-xl border bg-white p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-lg">Scan</h2>
            <StatusBadge status={scan?.status ?? "idle"} />
          </div>

          {scan?.started_at && (
            <p className="text-sm text-gray-500">
              Dernier : {formatRelativeDate(scan.finished_at ?? scan.started_at)}
              {scan.products_found != null && ` — ${scan.products_found} produits`}
            </p>
          )}
          {scan?.error && (
            <p className="text-sm text-red-600 truncate" title={scan.error}>
              {scan.error}
            </p>
          )}

          <button
            onClick={() => runScan.mutate()}
            disabled={scanning || runScan.isPending}
            className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {scanning ? (
              <>
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Scan en cours…
              </>
            ) : (
              "▶ Lancer un scan"
            )}
          </button>
        </div>

        {/* Cron card */}
        <div className="rounded-xl border bg-white p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-lg">Cron</h2>
            <StatusBadge status={cronActive ? "active" : "stopped"} />
          </div>

          {cronActive && intervalMin != null && (
            <p className="text-sm text-gray-500">
              Toutes les {intervalMin} min
              {nextRun && ` — prochain à ${nextRun}`}
            </p>
          )}

          <div className="flex gap-3">
            {!cronActive ? (
              <button
                onClick={() => startCron.mutate()}
                disabled={startCron.isPending}
                className="rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
              >
                ▶ Démarrer
              </button>
            ) : confirmStop ? (
              <>
                <button
                  onClick={() => stopCron.mutate()}
                  disabled={stopCron.isPending}
                  className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                >
                  Confirmer l&apos;arrêt
                </button>
                <button
                  onClick={() => setConfirmStop(false)}
                  className="rounded-lg border px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50"
                >
                  Annuler
                </button>
              </>
            ) : (
              <button
                onClick={() => setConfirmStop(true)}
                className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50"
              >
                ■ Stopper
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className="p-8 text-gray-400">Chargement…</div>}>
      <DashboardContent />
    </Suspense>
  );
}
