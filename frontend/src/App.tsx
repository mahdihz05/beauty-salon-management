import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
import { Route, Switch } from "wouter";
import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { RoleRoute } from "./auth/RoleRoute";
import { FoundationPage } from "./pages/FoundationPage";
import { ExplorePage } from "./pages/ExplorePage";
import { LoginPage } from "./pages/LoginPage";
import { CheckoutPlaceholderPage } from "./pages/booking/CheckoutPlaceholderPage";
import { BookingSuccessPage } from "./pages/booking/BookingSuccessPage";
import { DateTimeSelectionPage } from "./pages/booking/DateTimeSelectionPage";
import { ServiceSelectionPage } from "./pages/booking/ServiceSelectionPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { SalonProfilePage } from "./pages/SalonProfilePage";

const FavoritesPage = lazy(() =>
  import("./pages/FavoritesPage").then((m) => ({ default: m.FavoritesPage })),
);
const ProfilePage = lazy(() =>
  import("./pages/ProfilePage").then((m) => ({ default: m.ProfilePage })),
);
const MyBookingsPage = lazy(() =>
  import("./pages/MyBookingsPage").then((m) => ({ default: m.MyBookingsPage })),
);
const SupportTicketsPage = lazy(() =>
  import("./pages/SupportTicketsPage").then((m) => ({
    default: m.SupportTicketsPage,
  })),
);
const FinancePage = lazy(() =>
  import("./pages/FinancePage").then((m) => ({ default: m.FinancePage })),
);
const AdminDashboardPage = lazy(() =>
  import("./pages/admin/AdminDashboardPage").then((m) => ({
    default: m.AdminDashboardPage,
  })),
);
const AdminSalonsPage = lazy(() =>
  import("./pages/admin/AdminSalonsPage").then((m) => ({
    default: m.AdminSalonsPage,
  })),
);
const AdminSettingsPage = lazy(() =>
  import("./pages/admin/AdminSettingsPage").then((m) => ({
    default: m.AdminSettingsPage,
  })),
);
const AdminReviewsPage = lazy(() =>
  import("./pages/admin/AdminReviewsPage").then((m) => ({
    default: m.AdminReviewsPage,
  })),
);
const DashboardPage = lazy(() =>
  import("./pages/salon/DashboardPage").then((m) => ({
    default: m.DashboardPage,
  })),
);
const CalendarPage = lazy(() =>
  import("./pages/salon/CalendarPage").then((m) => ({
    default: m.CalendarPage,
  })),
);
const AvailabilityPage = lazy(() =>
  import("./pages/salon/AvailabilityPage").then((m) => ({
    default: m.AvailabilityPage,
  })),
);
const MyAvailabilityPage = lazy(() =>
  import("./pages/salon/MyAvailabilityPage").then((m) => ({
    default: m.MyAvailabilityPage,
  })),
);
const OnboardingPage = lazy(() =>
  import("./pages/salon/OnboardingPage").then((m) => ({
    default: m.OnboardingPage,
  })),
);
const ServicesPage = lazy(() =>
  import("./pages/salon/ServicesPage").then((m) => ({
    default: m.ServicesPage,
  })),
);
const StaffPage = lazy(() =>
  import("./pages/salon/StaffPage").then((m) => ({ default: m.StaffPage })),
);
const CustomersPage = lazy(() =>
  import("./pages/salon/CustomersPage").then((m) => ({
    default: m.CustomersPage,
  })),
);
const PromotionsPage = lazy(() =>
  import("./pages/salon/PromotionsPage").then((m) => ({
    default: m.PromotionsPage,
  })),
);

const ReportsPage = lazy(() =>
  import("./pages/salon/ReportsPage").then((module) => ({
    default: module.ReportsPage,
  })),
);

const AdminSalonDetailPage = lazy(() =>
  import("./pages/admin/AdminSalonDetailPage").then((module) => ({
    default: module.AdminSalonDetailPage,
  })),
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Suspense
          fallback={<div className="page-loader">در حال بارگذاری...</div>}
        >
          <Switch>
            <Route path="/" component={FoundationPage} />
            <Route path="/salons" component={ExplorePage} />
            <Route path="/salons/:slug" component={SalonProfilePage} />
            <Route
              path="/booking/:branchId/services"
              component={ServiceSelectionPage}
            />
            <Route
              path="/booking/:branchId/datetime"
              component={DateTimeSelectionPage}
            />
            <Route path="/booking/checkout">
              <ProtectedRoute>
                <CheckoutPlaceholderPage />
              </ProtectedRoute>
            </Route>
            <Route path="/booking/success/:bookingId">
              <ProtectedRoute>
                <BookingSuccessPage />
              </ProtectedRoute>
            </Route>
            <Route path="/login" component={LoginPage} />
            <Route path="/account/profile">
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            </Route>
            <Route path="/account/bookings">
              <ProtectedRoute>
                <MyBookingsPage />
              </ProtectedRoute>
            </Route>
            <Route path="/favorites">
              <ProtectedRoute>
                <FavoritesPage />
              </ProtectedRoute>
            </Route>
            <Route path="/account/support">
              <ProtectedRoute>
                <SupportTicketsPage />
              </ProtectedRoute>
            </Route>
            <Route path="/salon/dashboard">
              <RoleRoute roles={["salon_owner", "branch_manager"]}>
                <DashboardPage />
              </RoleRoute>
            </Route>
            <Route path="/salon/calendar">
              <RoleRoute
                roles={[
                  "salon_owner",
                  "branch_manager",
                  "receptionist",
                  "staff",
                ]}
              >
                <CalendarPage />
              </RoleRoute>
            </Route>
            <Route path="/salon/availability">
              <RoleRoute roles={["salon_owner", "branch_manager"]}>
                <AvailabilityPage />
              </RoleRoute>
            </Route>
            <Route path="/salon/my-availability">
              <RoleRoute roles={["staff"]}>
                <MyAvailabilityPage />
              </RoleRoute>
            </Route>
            <Route path="/salon/onboarding">
              <RoleRoute roles={["customer", "salon_owner"]}>
                <OnboardingPage />
              </RoleRoute>
            </Route>
            <Route path="/salon/services">
              <RoleRoute roles={["salon_owner", "branch_manager"]}>
                <ServicesPage />
              </RoleRoute>
            </Route>
            <Route path="/salon/staff">
              <RoleRoute roles={["salon_owner", "branch_manager"]}>
                <StaffPage />
              </RoleRoute>
            </Route>
            <Route path="/salon/customers">
              <RoleRoute roles={["salon_owner", "branch_manager"]}>
                <CustomersPage />
              </RoleRoute>
            </Route>
            <Route path="/salon/promotions">
              <RoleRoute roles={["salon_owner"]}>
                <PromotionsPage />
              </RoleRoute>
            </Route>
            <Route path="/salon/reports">
              <RoleRoute roles={["salon_owner", "branch_manager"]}>
                <Suspense
                  fallback={
                    <div className="page-loader">در حال بارگذاری گزارش...</div>
                  }
                >
                  <ReportsPage />
                </Suspense>
              </RoleRoute>
            </Route>
            <Route path="/admin/dashboard">
              <RoleRoute roles={["admin"]}>
                <AdminDashboardPage />
              </RoleRoute>
            </Route>
            <Route path="/admin/salons">
              <RoleRoute roles={["admin"]}>
                <AdminSalonsPage />
              </RoleRoute>
            </Route>
            <Route path="/admin/salons/:salonId">
              <RoleRoute roles={["admin"]}>
                <Suspense
                  fallback={
                    <div className="page-loader">
                      در حال بارگذاری اطلاعات سالن...
                    </div>
                  }
                >
                  <AdminSalonDetailPage />
                </Suspense>
              </RoleRoute>
            </Route>
            <Route path="/admin/settings">
              <RoleRoute roles={["admin"]}>
                <AdminSettingsPage />
              </RoleRoute>
            </Route>
            <Route path="/admin/reviews">
              <RoleRoute roles={["admin"]}>
                <AdminReviewsPage />
              </RoleRoute>
            </Route>
            <Route path="/admin/finance">
              <RoleRoute roles={["admin"]}>
                <FinancePage />
              </RoleRoute>
            </Route>
            <Route path="/admin/support">
              <RoleRoute roles={["admin"]}>
                <SupportTicketsPage />
              </RoleRoute>
            </Route>
            <Route component={NotFoundPage} />
          </Switch>
        </Suspense>
      </AuthProvider>
    </QueryClientProvider>
  );
}
