import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/navbar";
import { Providers } from "@/components/providers";
import { Toaster } from "sonner";

export const metadata: Metadata = {
  title: "Showroom Deals Agent",
  description: "Détecteur de vrais bons plans Showroomprivé",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className="bg-gray-50 text-gray-900">
        <Providers>
          <Navbar />
          <main className="mx-auto max-w-7xl px-4 py-8">{children}</main>
          <Toaster richColors position="top-right" />
        </Providers>
      </body>
    </html>
  );
}
