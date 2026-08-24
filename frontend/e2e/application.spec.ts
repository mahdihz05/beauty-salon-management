import { expect, test, type Page } from "@playwright/test";

async function expectNoHorizontalOverflow(page: Page) {
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    )
    .toBe(true);
}

async function loginWithMockOtp(page: Page, phone: string, next: string) {
  await page.goto(`/login?next=${encodeURIComponent(next)}`);
  await page.locator("#phone").fill(phone);
  await page.locator("form .button-primary").click();
  const debugAlert = page.locator(".alert-info");
  await expect(debugAlert).toBeVisible();
  const code = (await debugAlert.textContent())?.match(/\d{6}/)?.[0];
  expect(code).toBeTruthy();
  await page.locator("#code").fill(code!);
  await page.locator("form .button-primary").click();
  await expect(page).toHaveURL(new RegExp(`${next.replaceAll("/", "\\/")}$`));
}

test("public customer journey renders live demo data", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  if (testInfo.project.name !== "mobile-edge") {
    await expect(page.locator(".public-logo .brand-logo-mark")).toBeVisible();
    await expect(page.locator(".public-logo")).toContainText("Salovina");
  } else {
    await expect(
      page.locator(".mobile-home-brand .brand-logo-mark"),
    ).toBeVisible();
    await expect(page.locator(".mobile-home-brand")).toContainText("Salovina");
  }
  await expect(page.locator(".home-salon-grid article").first()).toBeVisible();
  await expect(page.locator(".home-salon-grid")).not.toContainText(
    "شروع قیمت از",
  );
  await expect(page.locator("body")).toContainText("سالن رزگلد");
  await expect
    .poll(() => page.locator(".category-strip a").count())
    .toBeGreaterThanOrEqual(12);
  await page.locator(".category-strip a").nth(2).click();
  await expect(page).toHaveURL(/\/salons\?category=\d+$/);
  await expect(page.locator(".explore-results article").first()).toBeVisible();
  await expect(page.getByText("نمایش روی نقشه")).toHaveCount(0);
  await expectNoHorizontalOverflow(page);

  await page.goto("/salons/demo-rose-gold");
  await expect(page.locator("h1")).toContainText("سالن رزگلد");
  await expect(page.locator(".public-service-row").first()).toBeVisible();
  await expect(page.locator(".salon-info-card")).toContainText("آدرس");
  await expect(page.locator(".salon-info-card p").first()).not.toContainText(
    "ثبت نشده",
  );
  await expectNoHorizontalOverflow(page);
  await page.screenshot({
    path: testInfo.outputPath("public-salon-profile.png"),
    fullPage: true,
  });
});

test("mock OTP opens the customer account", async ({ page }, testInfo) => {
  const phone = `0935${String(Date.now() + testInfo.workerIndex).slice(-7)}`;
  await loginWithMockOtp(page, phone, "/account/bookings");
  await expect(page.locator("h1")).toContainText("رزروهای من");
  await expect(page.locator(".wallet-pill")).toBeVisible();
});

test("customer completes service selection, OTP, hold and mock payment", async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== "desktop-edge",
    "The complete booking flow is covered once; responsive pages are tested separately.",
  );
  await page.goto("/booking/1/services");
  await page.locator(".select-service-card").first().click();
  await page.locator(".booking-summary .button-primary").click();

  const slots = page.locator(".time-grid button");
  const dateButtons = page.locator(".date-strip button");
  for (let index = 1; index < (await dateButtons.count()); index += 1) {
    if ((await slots.count()) > 0) break;
    const availabilityResponse = page.waitForResponse((response) =>
      response.url().includes("/api/bookings/availability/"),
    );
    await dateButtons.nth(index).click();
    await availabilityResponse;
  }
  const firstSlot = slots.first();
  await expect(firstSlot).toBeVisible();
  await firstSlot.click();
  await page.locator(".booking-summary button.button-primary").click();
  await expect(page).toHaveURL(/\/login\?next=/);

  const phone = `0936${String(Date.now() + testInfo.workerIndex).slice(-7)}`;
  await loginWithMockOtp(page, phone, "/booking/1/datetime");
  await page.locator(".booking-summary button.button-primary").click();
  await expect(page).toHaveURL(/\/booking\/checkout\?booking=\d+$/);

  await page.locator(".checkout-total .button-primary").click();
  await expect(page).toHaveURL(/\/booking\/success\/\d+\?payment=\d+$/);
  await expect(page.locator(".booking-success h1")).toContainText(
    "نوبت شما قطعی شد",
  );
});

test("owner dashboard uses live metrics instead of placeholders", async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== "desktop-edge",
    "Covered once to avoid concurrent OTP challenges.",
  );
  await loginWithMockOtp(page, "09120000002", "/salon/dashboard");
  await expect(page.locator(".salon-summary-card h2")).not.toBeEmpty();
  await expect(page.locator(".salon-summary-card")).toContainText("تأییدشده");
  await expect(page.locator(".stat-grid")).not.toContainText(
    "با راه‌اندازی موتور رزرو فعال می‌شود",
  );
  await expectNoHorizontalOverflow(page);
  await page.screenshot({
    path: testInfo.outputPath("owner-dashboard.png"),
    fullPage: true,
  });
});

test("admin dashboard loads protected live statistics", async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== "desktop-edge",
    "Covered once because the admin layout is desktop-oriented.",
  );
  await loginWithMockOtp(page, "09120000001", "/admin/dashboard");
  await expect(page.locator(".admin-stat-grid .admin-stat")).toHaveCount(6);
  await expect(page.locator(".admin-table")).toBeVisible();
  await expectNoHorizontalOverflow(page);

  await page.goto("/admin/salons");
  await expect(page.locator(".review-card").first()).toBeVisible();
  await page.locator(".admin-salon-details-link").first().click();
  await expect(page).toHaveURL(/\/admin\/salons\/\d+$/);
  await expect(page.locator(".admin-salon-metrics article")).toHaveCount(8);
  await expect(page.locator(".admin-detail-tabs button")).toHaveCount(7);
  await expectNoHorizontalOverflow(page);
  await page.screenshot({
    path: testInfo.outputPath("admin-salon-detail.png"),
    fullPage: true,
  });

  await page.goto("/admin/finance");
  await expect(page.locator(".finance-section")).toHaveCount(4);
  await expect(
    page.locator('.panel-nav-item[href="/admin/finance"]'),
  ).toHaveClass(/active/);
  await expectNoHorizontalOverflow(page);

  await page.goto("/admin/support");
  await expect(page.locator("h1")).toContainText("پشتیبانی و تیکت‌ها");
  await expect(
    page.locator('.panel-nav-item[href="/admin/support"]'),
  ).toHaveClass(/active/);
  await expectNoHorizontalOverflow(page);
});

test("receptionist can use calendar but cannot open financial or customer pages", async ({
  page,
}, testInfo) => {
  await loginWithMockOtp(page, "09120000007", "/salon/calendar");
  await expect(page.locator("h1")).toContainText("تقویم نوبت‌ها");
  await expect(
    page.locator('.panel-nav-item[href="/salon/reports"]'),
  ).toHaveCount(0);
  await expect(
    page.locator('.panel-nav-item[href="/salon/customers"]'),
  ).toHaveCount(0);
  if (testInfo.project.name === "desktop-edge") {
    await expect(page.locator(".booking-table-wrap")).toBeVisible();
    await expect(page.locator(".booking-mobile-list")).toBeHidden();
  } else {
    await expect(page.locator(".booking-table-wrap")).toBeHidden();
    await expect(page.locator(".booking-mobile-list")).toBeVisible();
  }
  await expectNoHorizontalOverflow(page);

  await page.goto("/salon/reports");
  await expect(page).toHaveURL(/\/$/);
});

test("staff can open only their personal availability", async ({
  page,
}, testInfo) => {
  await loginWithMockOtp(page, "09120000008", "/salon/my-availability");
  await expect(page.locator("h1")).toContainText("زمان‌های من");
  await expect(
    page.locator('.panel-nav-item[href="/salon/services"]'),
  ).toHaveCount(0);
  await expect(page.locator(".staff-day-card")).toHaveCount(7);
  await expect(page.locator(".staff-duration-section")).toBeVisible();
  await expectNoHorizontalOverflow(page);
  await page.screenshot({
    path: testInfo.outputPath("staff-availability-responsive.png"),
    fullPage: true,
  });
  await page.goto("/salon/services");
  await expect(page).toHaveURL(/\/$/);
});

test("mobile pages keep navigation visible without horizontal overflow", async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== "mobile-edge",
    "Mobile-only viewport assertion.",
  );
  await page.goto("/");
  await expect(page.locator(".customer-mobile-nav")).toBeVisible();
  await expect(page.locator(".mobile-home-brand")).toContainText("Salovina");
  await expect(
    page.locator(".mobile-home-brand .brand-logo-mark"),
  ).toBeVisible();
  await expectNoHorizontalOverflow(page);
  await page.goto("/salons/demo-rose-gold");
  await expect(page.locator(".profile-actions .button-primary")).toBeVisible();
  await expectNoHorizontalOverflow(page);

  await page.goto("/salons");
  await expect(page.locator(".mobile-filter-toggle")).toBeVisible();
  await page.locator(".mobile-filter-toggle").click();
  await expect(page.locator(".filter-card.open")).toBeVisible();
  await expect
    .poll(() => page.locator(".filter-card fieldset label").count())
    .toBeGreaterThanOrEqual(4);
  await page.locator(".filter-categories label").nth(1).click();
  await expect(page.locator(".mobile-filter-toggle b")).toHaveText("1");
  await expectNoHorizontalOverflow(page);
  await page.locator(".mobile-filter-actions .button-primary").click();
  await expect(page.locator(".filter-card.open")).toHaveCount(0);
});

test("tablet keeps public and panel layouts usable without horizontal overflow", async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== "tablet-edge",
    "Tablet-only responsive assertions.",
  );

  for (const path of ["/", "/salons", "/salons/demo-rose-gold"]) {
    await page.goto(path);
    await expectNoHorizontalOverflow(page);
  }
  await expect(page.locator(".public-header")).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("tablet-public-profile.png"),
    fullPage: true,
  });

  await loginWithMockOtp(page, "09120000002", "/salon/dashboard");
  for (const path of [
    "/salon/dashboard",
    "/salon/calendar",
    "/salon/availability",
    "/salon/finance",
  ]) {
    await page.goto(path);
    await expect(page.locator("h1")).toBeVisible();
    await expectNoHorizontalOverflow(page);
    if (path === "/salon/calendar") {
      await expect(page.locator(".calendar-board")).toBeVisible();
      await page.screenshot({
        path: testInfo.outputPath("tablet-owner-calendar.png"),
        fullPage: true,
      });
    }
  }

  await page.evaluate(() => localStorage.clear());
  await loginWithMockOtp(page, "09120000001", "/admin/dashboard");
  for (const path of [
    "/admin/dashboard",
    "/admin/salons",
    "/admin/finance",
    "/admin/support",
  ]) {
    await page.goto(path);
    await expectNoHorizontalOverflow(page);
    if (path === "/admin/finance") {
      await expect(page.locator(".finance-section")).toHaveCount(4);
      await expect(
        page.locator(".finance-salon-grid button").first(),
      ).toBeVisible();
      await expect(page.locator(".finance-mobile-list").first()).toBeVisible();
      await page.screenshot({
        path: testInfo.outputPath("tablet-admin-finance.png"),
        fullPage: false,
      });
    }
  }
});

test("admin finance and support tabs stay responsive on mobile", async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== "mobile-edge",
    "Integrated admin tabs are verified on the mobile viewport.",
  );
  await loginWithMockOtp(page, "09120000001", "/admin/dashboard");
  await expect(
    page.locator('.panel-nav-item[href="/admin/finance"]'),
  ).toBeVisible();
  await expect(
    page.locator('.panel-nav-item[href="/admin/support"]'),
  ).toBeVisible();
  await expectNoHorizontalOverflow(page);

  await page.goto("/admin/finance");
  await expect(page.locator(".finance-section")).toHaveCount(4);
  await expectNoHorizontalOverflow(page);
  await expect(page.locator(".finance-mobile-list").first()).toBeVisible();
  await page.screenshot({
    path: testInfo.outputPath("mobile-admin-finance.png"),
    fullPage: false,
  });

  await page.goto("/admin/support");
  await expect(page.locator("h1")).toContainText("پشتیبانی و تیکت‌ها");
  await expectNoHorizontalOverflow(page);
});

test("salon availability settings are usable on mobile", async ({
  page,
}, testInfo) => {
  await loginWithMockOtp(page, "09120000002", "/salon/availability");
  await expect(page.locator("h1")).toContainText("ساعات قابل رزرو");
  await expect(page.locator(".weekly-hours-row")).toHaveCount(7);
  await expect(page.locator(".closure-form")).toBeVisible();
  await page.locator(".closure-reason input").fill("تست تعطیلی موبایل");
  await page.locator(".closure-form .button-primary").click();
  const createdClosure = page
    .locator(".closure-list article")
    .filter({ hasText: "تست تعطیلی موبایل" });
  await expect(createdClosure).toBeVisible();
  await createdClosure.getByRole("button", { name: "حذف بازه بسته" }).click();
  await expect(createdClosure).toHaveCount(0);
  await expectNoHorizontalOverflow(page);
  await page.screenshot({
    path: testInfo.outputPath("salon-availability-responsive.png"),
    fullPage: true,
  });
});
