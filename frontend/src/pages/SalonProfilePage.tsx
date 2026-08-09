import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BadgeCheck,
  Clock3,
  Heart,
  MapPin,
  Phone,
  Share2,
  Star,
  UserRound,
} from "lucide-react";
import { useMemo } from "react";
import { Link, useRoute } from "wouter";
import { api, getApiError } from "../api/client";
import { useAuth } from "../auth/useAuth";
import { MobileBottomNav, PublicHeader } from "../components/PublicHeader";
import { faNumber, toman } from "../lib/format";
import type {
  Favorite,
  PublicBranchService,
  PublicSalon,
} from "../types/public";
import type { Paginated } from "../types/salon";
import type { Review } from "../types/booking";

export function SalonProfilePage() {
  const [, params] = useRoute("/salons/:slug");
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const salon = useQuery({
    queryKey: ["public", "salon", params?.slug],
    enabled: Boolean(params?.slug),
    queryFn: async () =>
      (await api.get<PublicSalon>(`/public/salons/${params?.slug}/`)).data,
  });
  const favorites = useQuery({
    queryKey: ["favorites"],
    enabled: Boolean(user),
    queryFn: async () =>
      (await api.get<Paginated<Favorite>>("/public/favorites/")).data,
  });
  const reviews = useQuery({
    queryKey: ["public", "reviews", salon.data?.id],
    enabled: Boolean(salon.data?.id),
    queryFn: async () =>
      (
        await api.get<Paginated<Review>>(
          `/reviews/public/?salon=${salon.data?.id}`,
        )
      ).data,
  });
  const favorite = favorites.data?.results.find(
    (item) => item.salon === salon.data?.id,
  );
  const favoriteMutation = useMutation({
    mutationFn: async () => {
      if (!user) throw new Error("LOGIN_REQUIRED");
      if (favorite) return api.delete(`/public/favorites/${favorite.id}/`);
      return api.post("/public/favorites/", { salon: salon.data?.id });
    },
    async onSuccess() {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["favorites"] }),
        queryClient.invalidateQueries({ queryKey: ["public", "salon"] }),
      ]);
    },
  });
  const branch = salon.data?.branches?.[0];
  const grouped = useMemo(() => {
    const groups = new Map<string, PublicBranchService[]>();
    branch?.services.forEach((service) =>
      groups.set(service.category_name, [
        ...(groups.get(service.category_name) || []),
        service,
      ]),
    );
    return [...groups.entries()];
  }, [branch]);
  if (salon.isLoading)
    return <div className="page-loader">در حال دریافت اطلاعات سالن...</div>;
  if (salon.isError || !salon.data)
    return (
      <div className="page-loader">
        <p className="alert alert-error">{getApiError(salon.error)}</p>
      </div>
    );
  const data = salon.data;
  const images = data.images?.length
    ? data.images.map((item) => item.image)
    : [
        data.cover_image || "/images/salon-07.jpg",
        "/images/salon-08.jpg",
        "/images/salon-09.jpg",
        "/images/salon-10.jpg",
      ];

  return (
    <div className="customer-page">
      <PublicHeader />
      <main className="salon-profile container">
        <section className="profile-top">
          <div className="salon-identity">
            <div className="salon-logo">
              <BadgeCheck />
            </div>
            <div>
              <h1>
                {data.name} <BadgeCheck />
              </h1>
              <p>
                <Star fill="currentColor" />{" "}
                {faNumber.format(Number(data.rating_average || 4.8))}{" "}
                <span>·</span> {faNumber.format(data.review_count)} نظر{" "}
                <span>·</span> {data.city}، {data.district}
              </p>
            </div>
          </div>
          <div className="profile-actions">
            <button
              className="button button-outline"
              onClick={() => favoriteMutation.mutate()}
            >
              <Heart fill={favorite ? "currentColor" : "none"} />{" "}
              {favorite ? "علاقه‌مندی شد" : "علاقه‌مندی"}
            </button>
            <Link
              className="button button-primary"
              href={`/booking/${branch?.id}/services`}
            >
              دریافت نوبت
            </Link>
            <button className="share-button" aria-label="اشتراک‌گذاری">
              <Share2 />
            </button>
          </div>
        </section>
        <section className="salon-gallery">
          <img src={images[0]} alt={data.name} />
          {images.slice(1, 4).map((image, index) => (
            <img
              src={image}
              alt={`نمای ${index + 2} ${data.name}`}
              key={image}
            />
          ))}
        </section>
        <div className="profile-layout">
          <aside className="salon-info-card">
            <h2>اطلاعات سالن</h2>
            <div>
              <MapPin />
              <p>
                <strong>آدرس</strong>
                <span>{branch?.address || "ثبت نشده"}</span>
              </p>
            </div>
            <div>
              <Phone />
              <p>
                <strong>تماس</strong>
                <span dir="ltr">{branch?.phone || "-"}</span>
              </p>
            </div>
            <div>
              <Clock3 />
              <p>
                <strong>ساعات کاری</strong>
                <span>شنبه تا پنجشنبه، با رزرو قبلی</span>
              </p>
            </div>
          </aside>
          <section className="salon-content">
            <nav className="profile-tabs">
              <a className="active" href="#services">
                خدمات و رزرو
              </a>
              <a href="#about">درباره ما</a>
              <a href="#team">تیم آرایشگران</a>
              <a href="#reviews">
                نظرات ({faNumber.format(data.review_count)})
              </a>
            </nav>
            <div id="services" className="service-groups">
              {grouped.map(([category, services]) => (
                <section key={category}>
                  <h2>{category}</h2>
                  {services.map((service) => (
                    <article className="public-service-row" key={service.id}>
                      <div>
                        <h3>{service.service_name}</h3>
                        <p>
                          {service.description ||
                            "خدمات تخصصی با مواد حرفه‌ای و کیفیت تضمین‌شده"}
                        </p>
                        <span>
                          <Clock3 /> {faNumber.format(service.duration_minutes)}{" "}
                          دقیقه
                        </span>
                      </div>
                      <div>
                        <strong>
                          {service.price_type === "starting_from" && "از "}
                          {toman(service.price)}
                        </strong>
                        <Link
                          className="button button-outline"
                          href={`/booking/${branch?.id}/services?service=${service.id}`}
                        >
                          رزرو
                        </Link>
                      </div>
                    </article>
                  ))}
                </section>
              ))}
            </div>
            <section id="team" className="public-team">
              <h2>تیم متخصص</h2>
              <div>
                {branch?.staff.map((person) => (
                  <article key={person.id}>
                    <span>
                      {person.photo ? (
                        <img src={person.photo} alt={person.full_name} />
                      ) : (
                        <UserRound />
                      )}
                    </span>
                    <strong>{person.full_name}</strong>
                    <small>
                      {faNumber.format(person.experience_years)} سال تجربه
                    </small>
                  </article>
                ))}
              </div>
            </section>
            <section id="reviews" className="public-reviews">
              <div className="section-title-row">
                <h2>نظر مشتریان</h2>
                <span>
                  <Star fill="currentColor" />{" "}
                  {faNumber.format(Number(data.rating_average))}
                </span>
              </div>
              <div className="public-review-list">
                {reviews.data?.results.map((review) => (
                  <article key={review.id}>
                    <div>
                      <strong>{review.customer_name}</strong>
                      <span>
                        <Star fill="currentColor" />{" "}
                        {faNumber.format(review.overall_rating)}
                      </span>
                    </div>
                    <p>{review.comment}</p>
                    <small>
                      کیفیت {faNumber.format(review.quality_rating)} · پاکیزگی{" "}
                      {faNumber.format(review.cleanliness_rating)} · رفتار{" "}
                      {faNumber.format(review.behavior_rating)}
                    </small>
                    {review.images.length > 0 && (
                      <div className="review-images">
                        {review.images.map((item) => (
                          <img
                            src={item.image}
                            alt="تصویر نظر مشتری"
                            key={item.id}
                          />
                        ))}
                      </div>
                    )}
                  </article>
                ))}
                {!reviews.isLoading && reviews.data?.count === 0 && (
                  <div className="summary-empty">
                    <Star />
                    <p>هنوز نظری منتشر نشده است.</p>
                  </div>
                )}
              </div>
            </section>
          </section>
        </div>
      </main>
      <MobileBottomNav />
    </div>
  );
}
