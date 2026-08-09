import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, EyeOff, Star } from "lucide-react";
import { useState } from "react";
import { api, getApiError } from "../../api/client";
import { AdminLayout } from "../../components/AdminLayout";
import { faNumber } from "../../lib/format";
import type { Review } from "../../types/booking";
import type { Paginated } from "../../types/salon";

export function AdminReviewsPage() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState("pending");
  const reviews = useQuery({
    queryKey: ["admin", "reviews", filter],
    queryFn: async () =>
      (
        await api.get<Paginated<Review>>(
          `/reviews/moderation/?status=${filter}`,
        )
      ).data,
  });
  const moderation = useMutation({
    mutationFn: ({
      id,
      status,
    }: {
      id: number;
      status: "published" | "hidden";
    }) => api.post(`/reviews/moderation/${id}/moderate/`, { status }),
    async onSuccess() {
      await queryClient.invalidateQueries({ queryKey: ["admin", "reviews"] });
    },
  });
  return (
    <AdminLayout title="مدیریت نظرات">
      <div className="admin-toolbar">
        <select
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
        >
          <option value="pending">در انتظار بررسی</option>
          <option value="published">منتشرشده</option>
          <option value="hidden">مخفی‌شده</option>
        </select>
      </div>
      {(reviews.isError || moderation.isError) && (
        <p className="alert alert-error">
          {getApiError(reviews.error || moderation.error)}
        </p>
      )}
      <section className="review-grid">
        {reviews.data?.results.map((review) => (
          <article className="review-card" key={review.id}>
            <div className="review-card-head">
              <div>
                <h2>{review.salon_name}</h2>
                <p>{review.customer_name}</p>
              </div>
              <strong className="review-stars">
                <Star fill="currentColor" />
                {faNumber.format(review.overall_rating)}
              </strong>
            </div>
            <p className="review-description">{review.comment}</p>
            <dl>
              <div>
                <dt>کیفیت</dt>
                <dd>{faNumber.format(review.quality_rating)}</dd>
              </div>
              <div>
                <dt>پاکیزگی</dt>
                <dd>{faNumber.format(review.cleanliness_rating)}</dd>
              </div>
              <div>
                <dt>رفتار</dt>
                <dd>{faNumber.format(review.behavior_rating)}</dd>
              </div>
            </dl>
            <div className="review-actions">
              {review.status !== "published" && (
                <button
                  className="button approve-button"
                  onClick={() =>
                    moderation.mutate({ id: review.id, status: "published" })
                  }
                >
                  <Check size={17} /> انتشار
                </button>
              )}
              {review.status !== "hidden" && (
                <button
                  className="button reject-button"
                  onClick={() =>
                    moderation.mutate({ id: review.id, status: "hidden" })
                  }
                >
                  <EyeOff size={17} /> مخفی‌سازی
                </button>
              )}
            </div>
          </article>
        ))}
      </section>
    </AdminLayout>
  );
}
