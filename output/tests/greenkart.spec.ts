import {test, expect} from '@playwright/test';

test.describe('GreenKart E2E – Promo Code & Checkout', () => {
    test('KAN-5: Discount code rahulshettyacademy applies correctly', async ({page}) => {
        // ── 1. Navigate to the homepage ──────────────────────────────────────────
        await page.goto('https://rahulshettyacademy.com/seleniumPractise/#/');

        // ASSERTION 1: Page title
        await expect(page).toHaveTitle('GreenKart - veg and fruits kart');

        // ── 2. Add "Cauliflower" to cart ─────────────────────────────────────────
        // Use null-safe card-level click so only the matching product is targeted
        const addResult = await page.evaluate(() => {
            const card = Array.from(document.querySelectorAll('.product')).find(
                (c) => c.querySelector('h4.product-name')?.textContent?.includes('Cauliflower')
            );
            if (card) (card.querySelector('.product-action button') as HTMLButtonElement).click();
            return card ? 'clicked' : 'not found';
        });
        expect(addResult).toBe('clicked');

        // ASSERTION 2: Cart badge shows 1 item
        const cartBadge = page.locator('.cart-info strong').first();
        await expect(cartBadge).toHaveText('1');

        // ── 3. Open mini-cart and proceed to checkout ────────────────────────────
        await page.click('a.cart-icon');
        await page.click('button:has-text("PROCEED TO CHECKOUT")');

        // Wait for the cart page to fully render
        await page.waitForURL('**/seleniumPractise/#/cart');

        // ASSERTION 3: URL contains /cart
        expect(page.url()).toContain('/cart');

        // ── 4. Capture original total before discount ────────────────────────────
        const totAmtText = await page.locator('span.totAmt').textContent();
        const originalTotal = parseFloat(totAmtText!.trim());
        expect(originalTotal).toBeGreaterThan(0);

        // ── 5. Apply promo code ──────────────────────────────────────────────────
        await page.fill('input.promoCode', 'rahulshettyacademy');
        await page.click('button.promoBtn');

        // Wait for the "Applying…" spinner to disappear before reading result
        await page.locator('text=Applying').waitFor({state: 'hidden'});

        // ASSERTION 4: Promo info message
        const promoInfo = page.locator('span.promoInfo');
        await expect(promoInfo).toHaveText('Code applied ..!');

        // ASSERTION 5: Discounted amount < original total
        const discountAmtText = await page.locator('span.discountAmt').textContent();
        const discountedTotal = parseFloat(discountAmtText!.trim());
        expect(discountedTotal).toBeLessThan(originalTotal);

        // ── 6. Place Order ───────────────────────────────────────────────────────
        await page.click('button:has-text("Place Order")');
        await page.waitForURL('**/seleniumPractise/#/country');
        await page.getByText('Choose Country').first().waitFor({state: 'visible'});

        // ── 7. Select country & accept terms ────────────────────────────────────
        await page.selectOption('select', {label: 'India'});
        await page.check('input.chkAgree');

        // ── 8. Proceed & capture order confirmation ──────────────────────────────
        // Combine click + assertion in a single waitForSelector to catch the
        // brief confirmation banner (disappears within ~3 s before redirect)
        const confirmed = await page.evaluate(async () => {
            // Trigger via DOM so evaluate and the click happen atomically
            const btn = document.querySelector('button') as HTMLButtonElement;
            // Find the Proceed button specifically
            const proceed = Array.from(document.querySelectorAll('button')).find(
                (b) => b.textContent?.trim() === 'Proceed'
            ) as HTMLButtonElement | undefined;
            if (proceed) proceed.click();
            return proceed ? 'clicked' : 'not found';
        });
        expect(confirmed).toBe('clicked');

        // ASSERTION 6: Order confirmation message visible
        await expect(
            page.locator('text=Thank you, your order has been placed successfully')
        ).toBeVisible({timeout: 8000});
    });
});