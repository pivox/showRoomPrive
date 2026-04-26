import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[40vh] gap-4 text-center">
      <h2 className="text-xl font-semibold text-gray-800">Page introuvable</h2>
      <p className="text-sm text-gray-500">Cette page n&apos;existe pas.</p>
      <Link
        href="/dashboard"
        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
      >
        Retour au dashboard
      </Link>
    </div>
  );
}
