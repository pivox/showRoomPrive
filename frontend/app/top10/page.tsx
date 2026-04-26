"use client";

import { Suspense, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { formatEur, formatPct, formatRelativeDate } from "@/lib/utils";
import { StatusBadge } from "@/components/status-badge";
import { ConfidenceBar } from "@/components/confidence-bar";
import type { AIJob, Product } from "@/lib/types";

function AICell({ product }: { product: Product }) {
  const status = product.ai_status;
  if (!status) return <span className="text-gray-400 text-xs">—</span>;
  return <StatusBadge status={status} />;
}

function DetailPanel({ job, onClose }: { job: AIJob; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex justify-end" onClick={onClose}>
      <div
        className="h-full w-full max-w-md bg-white shadow-2xl overflow-y-auto p-6 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-start">
          <h2 className="font-semibold text-base">{job.product_name}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-xl">✕</button>
        </div>
        <div className="text-sm text-gray-500">Provider : {job.provider}</div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-gray-400 mb-1">Verdict</div>
            {job.is_real_deal == null ? "—" : (
              <span className={job.is_real_deal ? "text-green-700 font-medium" : "text-red-700 font-medium"}>
                {job.is_real_deal ? "✓ Vrai deal" : "✗ Inflation prix"}
              </span>
            )}
          </div>
          <div>
            <div className="text-gray-400 mb-1">Confiance</div>
            <ConfidenceBar value={job.confidence} />
          </div>
          {job.real_market_price != null && (
            <div>
              <div className="text-gray-400 mb-1">Prix marché</div>
              <span className="font-medium">~{formatEur(job.real_market_price)}</span>
            </div>
          )}
        </div>
        {job.summary && (
          <div>
            <div className="text-gray-400 text-sm mb-1">Résumé</div>
            <p className="text-sm text-gray-700">{job.summary}</p>
          </div>
        )}
        {job.sources && job.sources.length > 0 && (
          <div>
            <div className="text-gray-400 text-sm mb-1">Sources ({job.sources.length})</div>
            <ul className="space-y-1">
              {job.sources.map((url, i) => (
                <li key={i}>
                  <a href={url} target="_blank" rel="noopener noreferrer"
                    className="text-blue-600 text-xs hover:underline break-all">{url}</a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

function Top10Content() {
  const qc = useQueryClient();
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [detailJob, setDetailJob] = useState<AIJob | null>(null);

  const { data: products = [], isFetching } = useQuery({
    queryKey: ["top10"],
    queryFn: () => api.getTop10().then((r) => r.data),
    refetchInterval: 60000,
  });

  const activeJobIds = products.flatMap((p) =>
    p.ai_status === "pending" || p.ai_status === "running" ? [p.id] : []
  );

  useQuery({
    queryKey: ["top10-ai-poll", activeJobIds],
    queryFn: async () => {
      qc.invalidateQueries({ queryKey: ["top10"] });
      return null;
    },
    enabled: activeJobIds.length > 0,
    refetchInterval: 3000,
  });

  const analyze = useMutation({
    mutationFn: (ids: number[]) => api.launchResearch(ids),
    onSuccess: (_, ids) => {
      toast.success(`${ids.length} analyse(s) IA lancée(s)`);
      qc.invalidateQueries({ queryKey: ["top10"] });
      setSelected(new Set());
    },
    onError: () => toast.error("Erreur lors du lancement de l'analyse"),
  });

  const allSelected = products.length > 0 && products.every((p) => selected.has(p.id));
  const toggleAll = () =>
    setSelected(allSelected ? new Set() : new Set(products.map((p) => p.id)));
  const toggleOne = (id: number) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Top 10 — Meilleures remises</h1>
        {isFetching && <span className="text-xs text-gray-400">↻ actualisation…</span>}
      </div>

      <div className="rounded-xl border bg-white shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="w-8 px-4 py-3">
                <input type="checkbox" checked={allSelected} onChange={toggleAll} />
              </th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">#</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Produit</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Marque</th>
              <th className="px-4 py-3 text-right font-medium text-gray-500">Showroom</th>
              <th className="px-4 py-3 text-right font-medium text-gray-500">Marque</th>
              <th className="px-4 py-3 text-right font-medium text-gray-500">Remise</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">IA</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {products.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                  Aucun produit — lancez un scan d&apos;abord.
                </td>
              </tr>
            ) : (
              products.map((p, i) => (
                <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <input type="checkbox" checked={selected.has(p.id)} onChange={() => toggleOne(p.id)} />
                  </td>
                  <td className="px-4 py-3 font-mono text-gray-400">{i + 1}</td>
                  <td className="px-4 py-3 max-w-xs">
                    {p.product_url ? (
                      <a href={p.product_url} target="_blank" rel="noopener noreferrer"
                        className="hover:text-blue-600 hover:underline truncate block">{p.name}</a>
                    ) : (
                      <span className="truncate block">{p.name}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{p.brand ?? "—"}</td>
                  <td className="px-4 py-3 text-right font-medium">{formatEur(p.showroom_price)}</td>
                  <td className="px-4 py-3 text-right text-gray-500">{formatEur(p.brand_price)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-green-700">{formatPct(p.real_discount)}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => {
                        if (p.ai_status === "done") {
                          api.getAIJob(p.id).then((r) => setDetailJob(r.data));
                        }
                      }}
                      className="cursor-pointer"
                    >
                      <AICell product={p} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex gap-3">
        <button
          onClick={() => analyze.mutate([...selected])}
          disabled={selected.size === 0 || analyze.isPending}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          🔍 Analyser la sélection ({selected.size})
        </button>
        {products.length > 0 && (
          <button
            onClick={() => analyze.mutate(products.map((p) => p.id))}
            disabled={analyze.isPending}
            className="rounded-lg border px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-40"
          >
            Analyser tout le top 10
          </button>
        )}
      </div>

      {detailJob && <DetailPanel job={detailJob} onClose={() => setDetailJob(null)} />}
    </div>
  );
}

export default function Top10Page() {
  return (
    <Suspense fallback={<div className="p-8 text-gray-400">Chargement…</div>}>
      <Top10Content />
    </Suspense>
  );
}
