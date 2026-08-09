import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ListTree, MapPin, Plus } from "lucide-react";
import { useState } from "react";
import { api, getApiError } from "../../api/client";
import { AdminLayout } from "../../components/AdminLayout";
import type { Category, City, Paginated } from "../../types/salon";

function makeSlug() {
  return `item-${Date.now()}`;
}

export function AdminSettingsPage() {
  const queryClient = useQueryClient();
  const [cityName, setCityName] = useState("");
  const [categoryName, setCategoryName] = useState("");
  const cities = useQuery({
    queryKey: ["admin", "cities"],
    queryFn: async () =>
      (await api.get<Paginated<City>>("/admin-panel/cities/")).data,
  });
  const categories = useQuery({
    queryKey: ["admin", "categories"],
    queryFn: async () =>
      (await api.get<Paginated<Category>>("/admin-panel/categories/")).data,
  });
  const cityMutation = useMutation({
    mutationFn: async () =>
      api.post("/admin-panel/cities/", { name: cityName, slug: makeSlug() }),
    async onSuccess() {
      setCityName("");
      await queryClient.invalidateQueries({ queryKey: ["admin", "cities"] });
    },
  });
  const categoryMutation = useMutation({
    mutationFn: async () =>
      api.post("/admin-panel/categories/", {
        name: categoryName,
        slug: makeSlug(),
      }),
    async onSuccess() {
      setCategoryName("");
      await queryClient.invalidateQueries({
        queryKey: ["admin", "categories"],
      });
    },
  });

  return (
    <AdminLayout title="تنظیمات پایه">
      {(cities.isError || categories.isError) && (
        <p className="alert alert-error">
          {getApiError(cities.error || categories.error)}
        </p>
      )}
      <section className="settings-grid">
        <article className="settings-card">
          <div className="settings-title">
            <span>
              <MapPin />
            </span>
            <div>
              <h2>شهرهای فعال</h2>
              <p>محدوده پوشش سامانه</p>
            </div>
          </div>
          <form
            className="inline-add"
            onSubmit={(event) => {
              event.preventDefault();
              cityMutation.mutate();
            }}
          >
            <input
              value={cityName}
              minLength={2}
              required
              placeholder="نام شهر جدید"
              onChange={(event) => setCityName(event.target.value)}
            />
            <button className="button button-primary" aria-label="افزودن شهر">
              <Plus />
            </button>
          </form>
          <ul className="settings-list">
            {cities.data?.results.map((city) => (
              <li key={city.id}>
                <span>{city.name}</span>
                <span className="status-badge success">فعال</span>
              </li>
            ))}
          </ul>
        </article>
        <article className="settings-card">
          <div className="settings-title">
            <span>
              <ListTree />
            </span>
            <div>
              <h2>دسته‌بندی خدمات</h2>
              <p>ساختار مرکزی خدمات</p>
            </div>
          </div>
          <form
            className="inline-add"
            onSubmit={(event) => {
              event.preventDefault();
              categoryMutation.mutate();
            }}
          >
            <input
              value={categoryName}
              minLength={2}
              required
              placeholder="دسته‌بندی جدید"
              onChange={(event) => setCategoryName(event.target.value)}
            />
            <button
              className="button button-primary"
              aria-label="افزودن دسته‌بندی"
            >
              <Plus />
            </button>
          </form>
          <ul className="settings-list">
            {categories.data?.results.map((category) => (
              <li key={category.id}>
                <span>{category.name}</span>
                <span className="status-badge success">فعال</span>
              </li>
            ))}
          </ul>
        </article>
      </section>
    </AdminLayout>
  );
}
