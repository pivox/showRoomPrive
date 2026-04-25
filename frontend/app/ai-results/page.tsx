"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { formatRelativeDate } from "@/lib/utils";
import { StatusBadge } from "@/components/status-badge";
import { ConfidenceBar } from "@/components/confidence-bar";
import type { AIJob } from "@/lib/types";

const PAGE_SIZE = 50;

function VerdictBadge({ job }: { job: AIJob }) {
  if (job.status !== "done" || job.is_real_deal == null) return null;
  return (
    <span className={`text-xs font-medium ${job.is_real_deal ? "text-green-700" : "text-red-700"}`}>
      {job.is_real_deal ? "✓ Vrai deal" : "✗ Inflation"}
    </span>
  );
}

function JobDrawer({ job, onClose, onRelaunch }: { job: AIJob; onClose: () => void; onRelaunch: (id: number) => void }) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/20" onClick={onClose}>
      <div
        className="h-full w-full max-w-md bg-white shadow-2xl overflow-y-auto p-6 space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-start">
          <div>
            <h2 className="font-semibold text-base">{job.product_name}</h2>
            <p className="text-xs text-gray-400 mt-0.5">Analyse {job.provider} — {formatRelativeDate(job.created_at)}</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-xl">✕</button>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-gray-400 text-xs mb-1">Verdict</div>
            <VerdictBadge job={job} />
            {job.status !== "done" && <StatusBadge status={job.status} />}
          </div>
          <div>
            <div className="text-gray-400 text-xs mb-1">Confiance</div>
            <ConfidenceBar value={job.confidence} />
          </div>
          {job.real_market_price != null && (
            <div>
              <div className="text-gray-400 text-xs mb-1">Prix marché</div>
              <span className="font-medium">
                ~{new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR" }).format(job.real_market_price)}
              </span>
            </div>
          )}
        </div>

        {job.summary && (
          <div>
            <div className="text-gray-400 text-xs mb-1">Résumé</div>
            <p className="text-sm text-gray-700 leading-relaxed">{job.summary}</p>
          </div>
        )}

        {job.sources && job.sources.length > 0 && (
          <div>
            <div className="text-gray-400 text-xs mb-2">Sources ({job.sources.length})</div>
            <ul className="space-y-1.5">
              {job.sources.map((url, i) => (
                <li key={i}>
                  <a href={url} target="_blank" rel="noopener noreferrer"
                    className="text-blue-600 text-xs hover:underline break-all">{url}</a>
                </li>
              ))}
            </ul>
          </div>
        )}

        {job.status === "error" && job.summary && (
          <div className="rounded-lg bg-red-50 p-3">
            <div className="text-xs font-medium text-red-700 mb-1">Erreur</div>
            <p className="text-xs text-red-600 break-all">{job.summary}</p>
          </div>
        )}

        <button
          onClick={() => onRelaunch(job.product_id)}
          className="w-full rounded-lg border border-blue-300 px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-50"
        >
          ↻ Relancer l&apos;analyse
        </button>
      </div>
    </div>
  );
}

export default function AIResultsPage() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [selected, setSelected] = useState<AIJob | null>(null);

  const { data, isFetching } = useQuery({
    queryKey: ["ai-results", { page, statusFilter }],
    queryFn: () =>
      api.getAIResults({
        page,
        page_size: PAGE_SIZE,
        ...(statusFilter ? { status: statusFilter } : {}),
      }).then((r) => r.data),
    refetchInterval: (q) => {
      const hasPending = q.state.data?.items.some(
        (j: AIJob) => j.status === "pending" || j.status === "running"
      );
      return hasPending ? 3000 : 30000;
    },
  });

  const relaunch = useMutation({
    mutationFn: (productId: number) => api.launchResearch([productId]),
    onSuccess: () => {
      toast.success("Nouvelle analyse lancée");
      qc.invalidateQueries({ queryKey: ["ai-results"] });
      setSelected(null);
    },
    onError: () => toast.error("Erreur lors du relancement"),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Résultats IA <span className="text-gray-400 text-lg font-normal">({total})</span></h1>
        {isFetching && <span className="text-xs text-gray-400">↻ actualisation…</span>}
      </div>

      {/* Filters */}
      <div className="rounded-xl border bg-white p-4 flex gap-4 items-end shadow-sm">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Statut</label>
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="rounded border px-2 py-1 text-sm"
          >
            <option value="">Tous</option>
            <option value="pending">En attente</option>
            <option value="running">En cours</option>
            <option value="done">Terminé</option>
            <option value="error">Erreur</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border bg-white shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Produit</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Provider</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Statut</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Confiance</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Verdict</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Date</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  Aucune analyse IA — lancez une analyse depuis Top 10 ou Articles.
                </td>
              </tr>
            ) : (
              items.map((job) => (
                <tr
                  key={job.job_id}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => setSelected(job)}
                >
                  <td className="px-4 py-3 max-w-xs truncate">{job.product_name}</td>
                  <td className="px-4 py-3 text-gray-500 capitalize">{job.provider}</td>
                  <td className="px-4 py-3"><StatusBadge status={job.status} /></td>
                  <td className="px-4 py-3"><ConfidenceBar value={job.confidence} /></td>
                  <td className="px-4 py-3"><VerdictBadge job={job} /></td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{formatRelativeDate(job.created_at)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex justify-end items-center gap-2 text-sm">
        <button onClick={() => setPage(page - 1)} disabled={page <= 1}
          className="px-3 py-1 rounded border disabled:opacity-40">←</button>
        <span className="text-gray-500">{page} / {totalPages}</span>
        <button onClick={() => setPage(page + 1)} disabled={page >= totalPages}
          className="px-3 py-1 rounded border disabled:opacity-40">→</button>
      </div>

      {selected && (
        <JobDrawer
          job={selected}
          onClose={() => setSelected(null)}
          onRelaunch={(id) => relaunch.mutate(id)}
        />
      )}
    </div>
  );
}
