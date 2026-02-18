CREATE TABLE IF NOT EXISTS products (
  id SERIAL PRIMARY KEY,
  source_product_id TEXT UNIQUE,
  name TEXT NOT NULL,
  brand TEXT,
  showroom_price NUMERIC(10,2) NOT NULL,
  displayed_discount NUMERIC(6,2),
  brand_price NUMERIC(10,2),
  real_discount NUMERIC(6,2),
  product_url TEXT,
  first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  last_checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  is_interesting BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_products_last_checked_at ON products(last_checked_at DESC);
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);

