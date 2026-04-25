import axios from "axios";
import type { AIJob, AIJobList, CronState, Product, ProductList, ScanState } from "./types";

const http = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
});

export const api = {
  runScan: () =>
    http.post<{ status: string; scan_id: string }>("/scan/run"),
  getScanStatus: () =>
    http.get<ScanState>("/scan/status"),

  startCron: () =>
    http.post<CronState>("/cron/start"),
  stopCron: () =>
    http.post<{ status: string }>("/cron/stop"),
  getCronStatus: () =>
    http.get<CronState>("/cron/status"),

  getTop10: () =>
    http.get<Product[]>("/products/top10"),
  getProducts: (params: Record<string, unknown>) =>
    http.get<ProductList>("/products", { params }),

  launchResearch: (ids: number[]) =>
    http.post("/ai/research", { product_ids: ids }),
  getAIJob: (jobId: number) =>
    http.get<AIJob>(`/ai/results/${jobId}`),
  getAIResults: (params: Record<string, unknown>) =>
    http.get<AIJobList>("/ai/results", { params }),
};
