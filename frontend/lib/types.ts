export interface Product {
  id: number;
  source_product_id: string | null;
  name: string;
  brand: string | null;
  showroom_price: number;
  displayed_discount: number | null;
  brand_price: number | null;
  real_discount: number | null;
  product_url: string | null;
  is_interesting: boolean;
  first_seen_at: string;
  last_checked_at: string;
  ai_status: "pending" | "running" | "done" | "error" | null;
}

export interface ProductList {
  total: number;
  page: number;
  page_size: number;
  items: Product[];
}

export type ScanStatus = "idle" | "running" | "done" | "error";

export interface ScanState {
  scan_id: string;
  status: ScanStatus;
  started_at: string | null;
  finished_at: string | null;
  products_found: number | null;
  error: string | null;
}

export interface CronState {
  active: boolean;
  interval_seconds: number;
  next_run_at: string | null;
  last_run_at: string | null;
}

export type AIJobStatus = "pending" | "running" | "done" | "error";

export interface AIJob {
  job_id: number;
  product_id: number;
  product_name: string;
  provider: string;
  status: AIJobStatus;
  is_real_deal: boolean | null;
  confidence: number | null;
  real_market_price: number | null;
  sources: string[] | null;
  summary: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface AIJobList {
  total: number;
  page: number;
  page_size: number;
  items: AIJob[];
}
