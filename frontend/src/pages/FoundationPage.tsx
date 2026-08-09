import { useQuery } from "@tanstack/react-query";
import {
  Brush,
  ChevronLeft,
  Flower2,
  Scissors,
  Search,
  Sparkles,
} from "lucide-react";
import { Link } from "wouter";
import { api, getApiError } from "../api/client";
import { MobileBottomNav, PublicHeader } from "../components/PublicHeader";
import { SalonCard } from "../components/SalonCard";
import type { Paginated } from "../types/salon";
import type { PublicCategory, PublicSalon } from "../types/public";

const categoryIcons = [Scissors, Brush, Flower2, Sparkles];

export function FoundationPage() {
  const salons = useQuery({
    queryKey: ["public", "home-salons"],
    queryFn: async () =>
      (
        await api.get<Paginated<PublicSalon>>(
          "/public/salons/?ordering=-rating_average",
        )
      ).data,
  });
  const categories = useQuery({
    queryKey: ["public", "categories"],
    queryFn: async () =>
      (await api.get<Paginated<PublicCategory>>("/public/categories/")).data,
  });
  const featured =
    salons.data?.results.find((item) => item.is_featured) ||
    salons.data?.results[0];

  return (
    <div className="customer-page">
      <PublicHeader />
      <main className="home-main container">
        <Link className="hero-search" href="/salons">
          <Search />
          <span>جستجوی آرایشگاه، خدمات...</span>
        </Link>
        <section className="category-strip" aria-label="دسته‌بندی خدمات">
          {categories.data?.results.map((category, index) => {
            const Icon = categoryIcons[index % categoryIcons.length];
            return (
              <Link href={`/salons?category=${category.id}`} key={category.id}>
                <span className={index === 0 ? "active" : ""}>
                  <Icon />
                </span>
                <strong>{category.name}</strong>
                <small>{category.salon_count} سالن</small>
              </Link>
            );
          })}
        </section>
        <section className="home-section">
          <div className="home-section-title">
            <h1>آرایشگاه‌های نزدیک شما</h1>
            <Link href="/salons">
              مشاهده همه <ChevronLeft size={17} />
            </Link>
          </div>
          {salons.isError && (
            <p className="alert alert-error">{getApiError(salons.error)}</p>
          )}
          <div className="home-salon-grid">
            {salons.data?.results.slice(0, 4).map((salon) => (
              <SalonCard salon={salon} key={salon.id} />
            ))}
          </div>
          {!salons.isLoading && salons.data?.count === 0 && (
            <div className="public-empty">
              <Scissors />
              <h2>سالن‌های منتخب به‌زودی اینجا هستند</h2>
              <p>پس از تأیید سالن‌ها توسط مدیر، امکان رزرو فعال می‌شود.</p>
            </div>
          )}
        </section>
        {featured && (
          <section className="featured-section">
            <h2>پیشنهاد ویژه استیچ</h2>
            <Link className="featured-card" href={`/salons/${featured.slug}`}>
              <img
                src={featured.cover_image || "/images/salon-03.jpg"}
                alt={featured.name}
              />
              <div>
                <span>پیشنهاد امروز</span>
                <h3>{featured.name}</h3>
                <p>
                  {featured.description || "خدمات تخصصی زیبایی با بهترین کیفیت"}
                </p>
              </div>
              <span className="featured-arrow">
                <ChevronLeft />
              </span>
            </Link>
          </section>
        )}
      </main>
      <MobileBottomNav />
    </div>
  );
}
