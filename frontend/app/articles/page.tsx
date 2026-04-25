"use client";

import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { formatEur, formatPct, formatRelativeDate } from "@/lib/utils";
import { StatusBadge } from "@/components/status-badge";

const PAGE_SIZE = 50;

export default function ArticlesPage() {
  const router = useRouter();
  const sp = useSearchParams();
  const qc = useQueryClient();

  const page = Number(sp.get("page") ?? 1);
  const brand = sp.get("brand") ?? "";
  const minDiscount = sp.get("min_discount") ?? "";
  const maxPrice = sp.get("max_price") ?? "";
  const interestingOnly = sp.get("interesting_only") === "true";
  const sort = sp.get("sort") ?? "last_checked_at";
  const order = sp.get("order") ?? "desc";

  const [selected, setSelected] = useState<Set<number>>(new Set());

  const updateParam = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(sp.toString());
      if (value) params.set(key, value); else params.delete(key);
      params.set("page", "1");
      router.push(`?${params.toString()}`);
    },
    [sp, router]
  );

  const { data, isFetching } = useQuery({
    queryKey: ["products", { page, brand, minDiscount, maxPrice, interestingOnly, sort, order }],
    queryFn: () =>
      api.getProducts({
        page,
        page_size: PAGE_SIZE,
        ...(brand ? { brand } : {}),
        ...(minDiscount ? { min_discount: minDiscount } : {}),
        ...(maxPrice ? { max_price: maxPrice } : {}),
        ...(interestingOnly ? { interesting_only: true } : {}),
        sort,
        order,
      }).then((r) => r.data),
    placeholderData: keepPreviousData,
  });

  const analyze = useMutation({
    mutationFn: (ids: number[]) => api.launchResearch(ids),
    onSuccess: (_, ids) => {
      toast.success(`${ids.length} analyse(s) IA lancée(s)`);
      qc.invalidateQueries({ queryKey: ["products"] });
      setSelected(new Set());
    },
    onError: () => toast.error("Erreur lors du lancement de l'analyse"),
  });

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const toggleOne = (id: number) =>
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const handleAnalyze = () => {
    const ids = [...selected];
    if (ids.length > 10) { toast.error("Maximum 10 articles à la fois"); return; }
    analyze.mutate(ids);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Articles <span className="text-gray-400 text-lg font-normal">({total})</span></h1>
        {isFetching && <span className="text-xs text-gray-400">↻ chargement…</span>}
      </div>

      {/* Filters */}
      <div className="rounded-xl border bg-white p-4 flex flex-wrap gap-3 items-end shadow-sm">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Marque</label>
          <input
            value={brand}
            onChange={(e) => updateParam("brand", e.target.value)}
            placeholder="ex: Nike"
            className="rounded border px-2 py-1 text-sm w-32"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Remise min %</label>
          <input
            type="number"
            value={minDiscount}
            onChange={(e) => updateParam("min_discount", e.target.value)}
            placeholder="40"
            className="rounded border px-2 py-1 text-sm w-20"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Prix max €</label>
          <input
            type="number"
            value={maxPrice}
            onChange={(e) => updateParam("max_price", e.target.value)}
            placeholder="150"
            className="rounded border px-2 py-1 text-sm w-24"
          />
        </div>
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={interestingOnly}
            onChange={(e) => updateParam("interesting_only", e.target.checked ? "true" : "")}
          />
          Offres intéressantes
        </label>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Tri</label>
          <select
            value={`${sort}-${order}`}
            onChange={(e) => {
              const [s, o] = e.target.value.split("-");
              const params = new URLSearchParams(sp.toString());
              params.set("sort", s); params.set("order", o); params.set("page", "1");
              router.push(`?${params.toString()}`);
            }}
            className="rounded border px-2 py-1 text-sm"
          >
            <option value="last_checked_at-desc">Plus récents</option>
            <option value="real_discount-desc">Remise ↓</option>
            <option value="real_discount-asc">Remise ↑</option>
            <option value="showroom_price-asc">Prix ↑</option>
            <option value="showroom_price-desc">Prix ↓</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border bg-white shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="w-8 px-4 py-3">
                <input type="checkbox" onChange={() => {}} checked={false} />
              </th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Produit</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Marque</th>
              <th className="px-4 py-3 text-right font-medium text-gray-500">Showroom</th>
              <th className="px-4 py-3 text-right font-medium text-gray-500">Remise</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">IA</th>
              <th className="px-4 py-3 text-left font-medium text-gray-500">Vu</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y">
            {items.length === 0 ? (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-gray-400">
                  Aucun article trouvé.
                </td>
              </tr>
            ) : (
              items.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3">
                    <input type="checkbox" checked={selected.has(p.id)} onChange={() => toggleOne(p.id)} />
                  </td>
                  <td className="px-4 py-3 max-w-xs">
                    {p.product_url ? (
                      <a href={p.product_url} target="_blank" rel="noopener noreferrer"
                        className="hover:text-blue-600 hover:underline truncate block">{p.name}</a>
                    ) : (
                      <span className="truncate block">{p.name}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500">{p.brand ?? "—"}</td>
                  <td className="px-4 py-3 text-right font-medium">{formatEur(p.showroom_price)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-green-700">{formatPct(p.real_discount)}</td>
                  <td className="px-4 py-3">
                    {p.ai_status ? <StatusBadge status={p.ai_status} /> : <span className="text-gray-300 text-xs">—</span>}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{formatRelativeDate(p.last_checked_at)}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => analyze.mutate([p.id])}
                      disabled={analyze.isPending}
                      className="text-xs text-blue-600 hover:underline disabled:opacity-40"
                    >
                      🔍 Analyser
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination + bulk action */}
      <div className="flex items-center justify-between">
        <button
          onClick={handleAnalyze}
          disabled={selected.size === 0 || analyze.isPending}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          🔍 Analyser la sélection ({selected.size})
          {selected.size > 10 && <span className="ml-1 text-red-200">⚠ max 10</span>}
        </button>

        <div className="flex items-center gap-2 text-sm">
          <button
            onClick={() => updateParam("page", String(page - 1))}
            disabled={page <= 1}
            className="px-3 py-1 rounded border disabled:opacity-40"
          >
            ←
          </button>
          <span className="text-gray-500">{page} / {totalPages}</span>
          <button
            onClick={() => updateParam("page", String(page + 1))}
            disabled={page >= totalPages}
            className="px-3 py-1 rounded border disabled:opacity-40"
          >
            →
          </button>
        </div>
      </div>
    </div>
  );
}
