"use client";

export function Loader() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center">
      <div className="relative">
        <div className="w-16 h-16 border-4 border-gray-200 rounded-full"></div>
        <div className="absolute top-0 left-0 w-16 h-16 border-4 border-transparent border-t-blue-500 rounded-full animate-spin"></div>
      </div>
      <p className="mt-4 text-gray-500">Yuklanmoqda...</p>
    </div>
  );
}

export function LoaderSmall() {
  return (
    <div className="flex items-center justify-center p-4">
      <div className="relative">
        <div className="w-8 h-8 border-2 border-gray-200 rounded-full"></div>
        <div className="absolute top-0 left-0 w-8 h-8 border-2 border-transparent border-t-blue-500 rounded-full animate-spin"></div>
      </div>
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`} />;
}

export function ProfileCardSkeleton() {
  return (
    <div className="card p-4 animate-fade-in">
      <div className="flex items-start gap-3">
        <Skeleton className="w-16 h-16 rounded-full" />
        <div className="flex-1">
          <Skeleton className="h-5 w-32 mb-2" />
          <Skeleton className="h-4 w-24 mb-2" />
          <Skeleton className="h-4 w-40" />
        </div>
      </div>
    </div>
  );
}
