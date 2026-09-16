import { test, expect } from "@playwright/test";

test.describe("Bilingual Internationalization (EN / FR)", () => {
  test("switches between English and French seamlessly with persistence and accessibility", async ({
    page,
  }) => {
    // 1. Visit root dashboard
    await page.goto("/");
    await page.waitForLoadState("domcontentloaded");

    // Verify initial HTML lang attribute is 'en' or set
    const initialLang = await page.evaluate(() => document.documentElement.lang);
    expect(["en", "fr"]).toContain(initialLang);

    // Find the language switcher button
    const langBtn = page.locator("#language-selector-button");
    await expect(langBtn).toBeVisible();

    // Switch to French
    await langBtn.click();
    const frOption = page.getByRole("option", { name: /Français/i });
    await expect(frOption).toBeVisible();
    await frOption.click();

    // Verify documentElement lang is updated to 'fr'
    await expect.poll(async () => {
      return page.evaluate(() => document.documentElement.lang);
    }).toBe("fr");

    // Verify localStorage has persisted 'fr'
    const storedLang = await page.evaluate(() =>
      localStorage.getItem("procureflow_language")
    );
    expect(storedLang).toBe("fr");

    // Verify key navigation and dashboard text in French
    await expect(page.getByRole("link", { name: "Vue d'ensemble" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Appels d'offres" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Matrice de comparaison" })).toBeVisible();

    // Reload page and verify persistence of French language
    await page.reload();
    await page.waitForLoadState("domcontentloaded");

    const reloadedLang = await page.evaluate(() => document.documentElement.lang);
    expect(reloadedLang).toBe("fr");
    await expect(page.getByRole("link", { name: "Appels d'offres" })).toBeVisible();

    // Switch back to English
    await langBtn.click();
    const enOption = page.getByRole("option", { name: /English/i });
    await expect(enOption).toBeVisible();
    await enOption.click();

    // Verify documentElement lang is updated to 'en'
    await expect.poll(async () => {
      return page.evaluate(() => document.documentElement.lang);
    }).toBe("en");

    const storedLangEn = await page.evaluate(() =>
      localStorage.getItem("procureflow_language")
    );
    expect(storedLangEn).toBe("en");

    // Verify English navigation
    await expect(page.getByRole("link", { name: "RFQs & Requests" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Comparison Matrix" })).toBeVisible();
  });
});
