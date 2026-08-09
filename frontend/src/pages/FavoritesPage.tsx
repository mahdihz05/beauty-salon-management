import { useQuery } from "@tanstack/react-query";
import { Heart } from "lucide-react";
import { api, getApiError } from "../api/client";
import { MobileBottomNav, PublicHeader } from "../components/PublicHeader";
import { SalonCard } from "../components/SalonCard";
import type { Favorite } from "../types/public";
import type { Paginated } from "../types/salon";

export function FavoritesPage() {
  const favorites = useQuery({
    queryKey: ["favorites"],
    queryFn: async () =>
      (await api.get<Paginated<Favorite>>("/public/favorites/")).data,
  });
  return (
    <div className="customer-page">
      <PublicHeader />
      <main className="favorites-page container">
        <div className="page-heading">
          <div>
            <h1>علاقه‌مندی‌ها</h1>
            <p>سالن‌هایی که برای بعد ذخیره کرده‌اید</p>
          </div>
        </div>
        {favorites.isError && (
          <p className="alert alert-error">{getApiError(favorites.error)}</p>
        )}
        <div className="home-salon-grid">
          {favorites.data?.results.map((item) => (
            <SalonCard
              salon={{ ...item.salon_details, is_favorite: true }}
              key={item.id}
            />
          ))}
        </div>
        {!favorites.isLoading && favorites.data?.count === 0 && (
          <div className="public-empty">
            <Heart />
            <h2>هنوز سالنی ذخیره نکرده‌اید</h2>
            <p>با لمس قلب روی کارت سالن، آن را به این صفحه اضافه کنید.</p>
          </div>
        )}
      </main>
      <MobileBottomNav />
    </div>
  );
}
