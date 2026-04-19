import { test, expect } from "@playwright/test";

test.describe("NoWires", () => {
  test("loads the map page", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "nowires" })).toBeVisible();
  });

  test("shows P2P tab by default", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Link Analysis" })).toBeVisible();
  });

  test("switches to Coverage tab", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("tab", { name: "Coverage" }).click();
    await expect(page.getByRole("heading", { name: "Coverage" })).toBeVisible();
  });

  test("P2P panel renders form inputs", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("input").first()).toBeVisible();
  });

  test("Coverage panel renders form inputs", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("tab", { name: "Coverage" }).click();
    await expect(page.getByRole("button", { name: "Compute Radius" })).toBeVisible();
  });
});