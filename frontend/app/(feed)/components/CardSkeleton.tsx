export function CardSkeleton() {
  return (
    <div className="bg-white rounded-xl p-4 shadow-sm animate-pulse">
      <div className="flex gap-2 mb-3">
        <div className="h-5 w-12 bg-gray-200 rounded-full" />
        <div className="h-5 w-16 bg-gray-200 rounded-full" />
      </div>
      <div className="h-5 bg-gray-200 rounded w-3/4 mb-2" />
      <div className="h-4 bg-gray-200 rounded w-full mb-1.5" />
      <div className="h-4 bg-gray-200 rounded w-5/6 mb-4" />
      <div className="flex gap-2">
        <div className="h-4 w-14 bg-gray-200 rounded-full" />
        <div className="h-4 w-10 bg-gray-200 rounded-full" />
      </div>
    </div>
  )
}

export function CardSkeletonList({ count = 6 }: { count?: number }) {
  return (
    <div className="flex flex-col gap-3 px-4 py-3">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  )
}
