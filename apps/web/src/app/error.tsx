"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center h-full bg-[#0f0f0f] text-white p-8">
      <h2 className="text-xl font-bold mb-2">Something went wrong</h2>
      <p className="text-sm text-gray-400 mb-4 max-w-md text-center">
        {error.message || "An unexpected error occurred."}
      </p>
      <button
        onClick={reset}
        className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded text-sm"
      >
        Try again
      </button>
    </div>
  );
}