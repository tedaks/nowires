"use client";

import { Button } from "@/components/ui/button";

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center h-full bg-background text-white p-8">
      <h2 className="text-xl font-bold mb-2">Something went wrong</h2>
      <p className="text-sm text-gray-400 mb-4 max-w-md text-center">
        {error.message || "An unexpected error occurred."}
      </p>
      <Button variant="outline" size="sm" onClick={reset}>
        Try again
      </Button>
    </div>
  );
}