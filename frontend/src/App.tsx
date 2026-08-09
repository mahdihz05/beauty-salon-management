import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
import { Route, Switch } from "wouter";
import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { RoleRoute } from "./auth/RoleRoute";
import { FoundationPage } from "./pages/FoundationPage";
import { ExplorePage } from "./pages/ExplorePage";
import { FavoritesPage } from "./pages/FavoritesPage";
import { LoginPage } from "./pages/LoginPage";
import { CheckoutPlaceholderPage } from "./pages/booking/CheckoutPlaceholderPage";
import { BookingSuccessPage } from "./pages/booking/BookingSuccessPage";
import { DateTimeSelectionPage } from "./pages/booking/DateTimeSelectionPage";
import { ServiceSelectionPage } from "./pages/booking/ServiceSelectionPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ProfilePage } from "./pages/ProfilePage";
import { SalonProfilePage } from "./pages/SalonProfilePage";
import { AdminDashboardPage } from "./pages/admin/AdminDashboardPage";
import { AdminSalonsPage } from "./pages/admin/AdminSalonsPage";
import { AdminSettingsPage } from "./pages/admin/AdminSettingsPage";
import { AdminReviewsPage } from "./pages/admin/AdminReviewsPage";
import { MyBookingsPage } from "./pages/MyBookingsPage";
import { SupportTicketsPage } from "./pages/SupportTicketsPage";
import { FinancePage } from "./pages/FinancePage";
import { DashboardPage } from "./pages/salon/DashboardPage";
import { CalendarPage } from "./pages/salon/CalendarPage";
import { OnboardingPage } from "./pages/salon/OnboardingPage";
import { ServicesPage } from "./pages/salon/ServicesPage";
import { StaffPage } from "./pages/salon/StaffPage";
import { CustomersPage } from "./pages/salon/CustomersPage";
import { PromotionsPage } from "./pages/salon/PromotionsPage";

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
          <Route path="/support/tickets">
            <RoleRoute roles={["support", "admin"]}>
              <SupportTicketsPage />
            </RoleRoute>
          </Route>
          <Route path="/finance/payments">
            <RoleRoute roles={["finance", "admin"]}>
              <FinancePage />
            </RoleRoute>
          </Route>
          <Route path="/salon/dashboard">
            <RoleRoute roles={["salon_owner", "branch_manager"]}>
              <DashboardPage />
            </RoleRoute>
          </Route>
          <Route path="/salon/calendar">
            <RoleRoute
              roles={["salon_owner", "branch_manager", "receptionist", "staff"]}
            >
              <CalendarPage />
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
          <Route component={NotFoundPage} />
        </Switch>
      </AuthProvider>
    </QueryClientProvider>
  );
}
