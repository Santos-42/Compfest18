import React from "react";

export default function LoadingSpinner({ message = "AI sedang menganalisis..." }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3" role="status" aria-live="polite">
      <div className="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin" aria-hidden="true" />
      <p className="text-sm text-gray-600">{message}</p>
    </div>
  );
}
