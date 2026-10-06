import { Stars } from '@/components/reviews/StarRating'
import type { Review } from '@/types'

export default function ReviewList({ reviews }: { reviews: Review[] }) {
  if (reviews.length === 0) {
    return <p className="text-sm text-muted-foreground">No reviews yet.</p>
  }
  return (
    <ul className="divide-y">
      {reviews.map((review, i) => (
        <li key={`${review.created_at}-${i}`} className="py-4 first:pt-0">
          <div className="flex items-center gap-2">
            <Stars value={review.rating} />
            <span className="text-sm font-medium">{review.parent_first_name}</span>
            <span className="text-xs text-muted-foreground">
              {new Date(review.updated_at).toLocaleDateString('en-GB', { month: 'short', year: 'numeric' })}
            </span>
          </div>
          {review.comment && <p className="mt-2 text-sm text-muted-foreground">{review.comment}</p>}
        </li>
      ))}
    </ul>
  )
}
