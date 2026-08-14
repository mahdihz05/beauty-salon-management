import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Clock3, LoaderCircle, Plus, Scissors } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { api, getApiError } from "../../api/client";
import { SalonLayout } from "../../components/SalonLayout";
import { faNumber, toman } from "../../lib/format";
import type {
  Branch,
  BranchService,
  Category,
  Paginated,
  Service,
} from "../../types/salon";

const schema = z.object({
  branch: z.number().positive(),
  category: z.number().positive("دسته‌بندی را انتخاب کنید."),
  name: z.string().min(2, "نام خدمت الزامی است."),
  price: z.number().positive("قیمت باید بیشتر از صفر باشد."),
  duration_minutes: z.number().min(15, "حداقل مدت خدمت ۱۵ دقیقه است."),
  price_type: z.enum(["fixed", "starting_from"]),
});
type ServiceForm = z.infer<typeof schema>;

export function ServicesPage() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [serverError, setServerError] = useState("");
  const form = useForm<ServiceForm>({
    resolver: zodResolver(schema),
    defaultValues: { duration_minutes: 45, price_type: "fixed" },
  });
  const branches = useQuery({
    queryKey: ["management", "branches"],
    queryFn: async () =>
      (await api.get<Paginated<Branch>>("/management/branches/")).data,
  });
  const categories = useQuery({
    queryKey: ["management", "categories"],
    queryFn: async () =>
      (await api.get<Category[]>("/management/categories/")).data,
  });
  const services = useQuery({
    queryKey: ["management", "branch-services"],
    queryFn: async () =>
      (await api.get<Paginated<BranchService>>("/management/branch-services/"))
        .data,
  });
  const createMutation = useMutation({
    mutationFn: async (values: ServiceForm) => {
      const branch = branches.data?.results.find(
        (item) => item.id === values.branch,
      );
      if (!branch) throw new Error("شعبه انتخاب‌شده پیدا نشد.");
      const service = (
        await api.post<Service>("/management/services/", {
          salon: branch.salon,
          category: values.category,
          name: values.name,
        })
      ).data;
      return (
        await api.post<BranchService>("/management/branch-services/", {
          branch: values.branch,
          service: service.id,
          price: values.price,
          price_type: values.price_type,
          duration_minutes: values.duration_minutes,
        })
      ).data;
    },
    async onSuccess() {
      await queryClient.invalidateQueries({
        queryKey: ["management", "branch-services"],
      });
      form.reset({
        branch: branches.data?.results[0]?.id,
        duration_minutes: 45,
        price_type: "fixed",
      });
      setShowForm(false);
    },
    onError(error) {
      setServerError(getApiError(error));
    },
  });
  const durationMutation = useMutation({
    mutationFn: async ({ id, duration }: { id: number; duration: number }) =>
      api.patch(`/management/branch-services/${id}/`, {
        duration_minutes: duration,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ["management", "branch-services"],
      }),
  });

  return (
    <SalonLayout
      title="مدیریت خدمات"
      description={`${faNumber.format(services.data?.count ?? 0)} خدمت ثبت‌شده`}
      action={
        <button
          className="button button-primary"
          onClick={() => setShowForm(true)}
        >
          <Plus size={19} /> افزودن خدمت
        </button>
      }
    >
      {showForm && (
        <form
          className="quick-form"
          onSubmit={form.handleSubmit((values) =>
            createMutation.mutate(values),
          )}
        >
          <div className="quick-form-head">
            <div>
              <h2>خدمت جدید</h2>
              <p>قیمت و مدت خدمت را برای شعبه مشخص کنید.</p>
            </div>
            <button
              type="button"
              className="text-button"
              onClick={() => setShowForm(false)}
            >
              بستن
            </button>
          </div>
          <div className="form-grid">
            <div className="field">
              <label>شعبه</label>
              <select {...form.register("branch", { valueAsNumber: true })}>
                <option value="">انتخاب شعبه</option>
                {branches.data?.results.map((branch) => (
                  <option value={branch.id} key={branch.id}>
                    {branch.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>دسته‌بندی</label>
              <select {...form.register("category", { valueAsNumber: true })}>
                <option value="">انتخاب دسته</option>
                {categories.data?.map((category) => (
                  <option value={category.id} key={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>نام خدمت</label>
              <input {...form.register("name")} />
            </div>
            <div className="field">
              <label>قیمت (تومان)</label>
              <input
                type="number"
                {...form.register("price", { valueAsNumber: true })}
              />
            </div>
            <div className="field">
              <label>مدت (دقیقه)</label>
              <input
                type="number"
                step="15"
                {...form.register("duration_minutes", { valueAsNumber: true })}
              />
            </div>
            <div className="field">
              <label>نوع قیمت</label>
              <select {...form.register("price_type")}>
                <option value="fixed">ثابت</option>
                <option value="starting_from">شروع از</option>
              </select>
            </div>
          </div>
          {serverError && <p className="alert alert-error">{serverError}</p>}
          <button
            className="button button-primary"
            disabled={createMutation.isPending}
          >
            {createMutation.isPending && (
              <LoaderCircle className="spin" size={18} />
            )}{" "}
            ذخیره خدمت
          </button>
        </form>
      )}
      {services.isError && (
        <p className="alert alert-error">{getApiError(services.error)}</p>
      )}
      <section className="management-list">
        {services.data?.results.map((service) => (
          <article className="management-row" key={service.id}>
            <span className="service-icon">
              <Scissors />
            </span>
            <div className="row-primary">
              <h3>{service.service_name}</h3>
              <p>
                {service.category_name} · {service.branch_name}
              </p>
            </div>
            <div className="row-meta">
              <span>
                <Clock3 size={16} /> {faNumber.format(service.duration_minutes)}{" "}
                دقیقه
              </span>
              <strong>
                {service.price_type === "starting_from" && "از "}
                {toman(service.price)}
              </strong>
            </div>
            <form
              className="inline-duration-form"
              onSubmit={(event) => {
                event.preventDefault();
                const duration = Number(
                  new FormData(event.currentTarget).get("duration"),
                );
                durationMutation.mutate({ id: service.id, duration });
              }}
            >
              <input
                aria-label={`مدت پایه ${service.service_name}`}
                name="duration"
                type="number"
                min="5"
                defaultValue={service.duration_minutes}
              />
              <button className="button button-outline">ثبت مدت پایه</button>
            </form>
            <span
              className={`status-badge ${service.is_active ? "success" : "neutral"}`}
            >
              {service.is_active ? "فعال" : "غیرفعال"}
            </span>
          </article>
        ))}
        {!services.isLoading && services.data?.count === 0 && (
          <div className="panel-empty">
            <Scissors size={36} />
            <h2>هنوز خدمتی ثبت نشده</h2>
            <p>اولین خدمت سالن را همراه قیمت و مدت اضافه کنید.</p>
          </div>
        )}
      </section>
    </SalonLayout>
  );
}
