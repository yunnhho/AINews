export function CardSkeleton() {
  return (
    <div className="bg-[#fbf9f3] border border-rule p-5 animate-pulse">
      <div className="flex gap-3 mb-3">
        <div className="h-3 w-16 bg-rule" />
        <div className="h-3 w-12 bg-rule" />
      </div>
      <div className="h-5 bg-rule w-3/4 mb-2.5" />
      <div className="h-3.5 bg-rule/70 w-full mb-1.5" />
      <div className="h-3.5 bg-rule/70 w-5/6 mb-4" />
      <div className="flex gap-3">
        <div className="h-3 w-14 bg-rule" />
        <div className="h-3 w-10 bg-rule" />
      </div>
    </div>
  )
}

export function CardSkeletonList({ count = 6 }: { count?: number }) {
  return (
    <div className="flex flex-col gap-3 py-4">
      {Array.from({ length: count }).map((_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  )
}
