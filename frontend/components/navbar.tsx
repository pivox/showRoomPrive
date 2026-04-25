"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const links = [
  { href: "/dashboard",  label: "Dashboard" },
  { href: "/top10",      label: "Top 10" },
  { href: "/articles",   label: "Articles" },
  { href: "/ai-results", label: "Résultats IA" },
];

export function Navbar() {
  const path = usePathname();
  return (
    <nav className="border-b bg-white px-6 py-3 flex items-center gap-8">
      <span className="font-bold text-gray-900 text-sm">Showroom Deals</span>
      <div className="flex gap-4">
        {links.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className={cn(
              "text-sm font-medium transition-colors hover:text-blue-600",
              path.startsWith(l.href) ? "text-blue-600" : "text-gray-500"
            )}
          >
            {l.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
