import { useQuery } from "@tanstack/react-query";
import { ChevronDown, ListFilter, RotateCcw, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { api, getApiError } from "../api/client";
import { MobileBottomNav, PublicHeader } from "../components/PublicHeader";
import { SalonCard } from "../components/SalonCard";
import type { Paginated } from "../types/salon";
import type { PublicCategory, PublicSalon } from "../types/public";

export function ExplorePage() {
  const initial = useMemo(
    () => new URLSearchParams(window.location.search),
    [],
  );
  const [search, setSearch] = useState(initial.get("search") || "");
  const [type, setType] = useState(initial.get("type") || "");
  const [category, setCategory] = useState(initial.get("category") || "");
  const [ordering, setOrdering] = useState("-rating_average");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const activeFilterCount = Number(Boolean(type)) + Number(Boolean(category));
  const query = new URLSearchParams({ ordering });
  if (search) query.set("search", search);
  if (type) query.set("type", type);
  if (category) query.set("category", category);
  const salons = useQuery({
    queryKey: ["public", "salons", query.toString()],
    queryFn: async () =>
      (await api.get<Paginated<PublicSalon>>(`/public/salons/?${query}`)).data,
  });
  const categories = useQuery({
    queryKey: ["public", "categories"],
    queryFn: async () =>
      (await api.get<Paginated<PublicCategory>>("/public/categories/")).data,
  });

  return (
    <div className="customer-page">
      <PublicHeader />
      <main className="explore-main container">
        <div className="mobile-search">
          <Search />
          <input
            value={search}
            placeholder="جستجوی سالن یا خدمت"
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        <div className="explore-toolbar">
          <label>
            مرتب‌سازی بر اساس:
            <select
              value={ordering}
              onChange={(event) => setOrdering(event.target.value)}
            >
              <option value="-rating_average">برترین</option>
              <option value="-created_at">جدیدترین</option>
            </select>
          </label>
        </div>
        <div className="explore-layout">
          <button
            className={`mobile-filter-toggle ${filtersOpen ? "open" : ""}`}
            onClick={() => setFiltersOpen((value) => !value)}
            aria-expanded={filtersOpen}
            aria-controls="salon-filters"
          >
            <span>
              <ListFilter /> فیلتر سالن‌ها
              {activeFilterCount > 0 && <b>{activeFilterCount}</b>}
            </span>
            <ChevronDown />
          </button>
          <aside
            id="salon-filters"
            className={`filter-card ${filtersOpen ? "open" : ""}`}
          >
            <h2>
              <ListFilter /> فیلترها
            </h2>
            <fieldset className="filter-type">
              <legend>جنسیت</legend>
              {[
                ["", "هر دو"],
                ["women", "زنانه"],
                ["men", "مردانه"],
              ].map(([value, label]) => (
                <label key={label}>
                  <input
                    type="radio"
                    name="type"
                    value={value}
                    checked={type === value}
                    onChange={() => setType(value)}
                  />{" "}
                  {label}
                </label>
              ))}
            </fieldset>
            <fieldset className="filter-categories">
              <legend>دسته‌بندی خدمات</legend>
              <label>
                <input
                  type="radio"
                  name="category"
                  checked={!category}
                  onChange={() => setCategory("")}
                />{" "}
                همه دسته‌ها
              </label>
              {categories.data?.results.map((item) => (
                <label key={item.id}>
                  <input
                    type="radio"
                    name="category"
                    checked={category === String(item.id)}
                    onChange={() => setCategory(String(item.id))}
                  />{" "}
                  {item.name} ({item.salon_count})
                </label>
              ))}
            </fieldset>
            <div className="mobile-filter-actions">
              <button
                type="button"
                className="button button-outline"
                disabled={activeFilterCount === 0}
                onClick={() => {
                  setType("");
                  setCategory("");
                }}
              >
                <RotateCcw size={17} /> پاک‌کردن فیلترها
              </button>
              <button
                type="button"
                className="button button-primary"
                onClick={() => setFiltersOpen(false)}
              >
                نمایش {salons.data?.count ?? 0} سالن
              </button>
            </div>
          </aside>
          <section className="explore-results">
            {salons.isError && (
              <p className="alert alert-error">{getApiError(salons.error)}</p>
            )}
            {salons.data?.results.map((salon) => (
              <SalonCard salon={salon} key={salon.id} />
            ))}
            {!salons.isLoading && salons.data?.count === 0 && (
              <div className="public-empty">
                <Search />
                <h2>سالنی با این مشخصات پیدا نشد</h2>
                <p>فیلترها را تغییر دهید و دوباره امتحان کنید.</p>
              </div>
            )}
          </section>
        </div>
      </main>
      <MobileBottomNav />
    </div>
  );
}
