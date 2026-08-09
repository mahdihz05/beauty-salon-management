import { BadgeCheck, Heart, MapPin, Star } from "lucide-react";
import { Link } from "wouter";
import { faNumber, toman } from "../lib/format";
import type { PublicSalon } from "../types/public";

function fallbackImage(id: number) {
  return `/images/salon-${String(((id - 1) % 12) + 1).padStart(2, "0")}.jpg`;
}

export function SalonCard({
  salon,
  compact = false,
}: {
  salon: PublicSalon;
  compact?: boolean;
}) {
  return (
    <article className={`public-salon-card ${compact ? "compact" : ""}`}>
      <Link className="salon-card-image" href={`/salons/${salon.slug}`}>
        <img
          src={salon.cover_image || fallbackImage(salon.id)}
          alt={`نمای ${salon.name}`}
        />
        <span className="rating-pill">
          <Star size={14} fill="currentColor" />{" "}
          {faNumber.format(Number(salon.rating_average || 4.8))}
        </span>
      </Link>
      <div className="salon-card-body">
        <div className="salon-card-title">
          <h3>
            <Link href={`/salons/${salon.slug}`}>{salon.name}</Link>
          </h3>
          <BadgeCheck size={18} />
          <Heart size={18} className={salon.is_favorite ? "favorite" : ""} />
        </div>
        <p>
          <MapPin size={15} /> {salon.city}
          {salon.district ? `، ${salon.district}` : ""}
        </p>
        <div className="salon-card-footer">
          <div>
            <span>شروع قیمت از</span>
            <strong>
              {salon.min_price ? toman(salon.min_price) : "تماس بگیرید"}
            </strong>
          </div>
          <Link
            className="button button-primary"
            href={`/salons/${salon.slug}`}
          >
            رزرو وقت
          </Link>
        </div>
      </div>
    </article>
  );
}
