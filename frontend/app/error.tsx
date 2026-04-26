"use client";

import { useEffect } from "react";

interface Props {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: Props) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[40vh] gap-4 text-center">
      <h2 className="text-xl font-semibold text-gray-800">Une erreur est survenue</h2>
      <p className="text-sm text-gray-500 max-w-md">
        {error.message || "Erreur inattendue. Vérifiez que l'API backend est démarrée."}
      </p>
      <button
        onClick={reset}
        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
      >
        Réessayer
      </button>
    </div>
  );
}
