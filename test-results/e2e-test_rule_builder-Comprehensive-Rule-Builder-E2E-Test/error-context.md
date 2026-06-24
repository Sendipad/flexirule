# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: e2e/test_rule_builder.spec.js >> Comprehensive Rule Builder E2E Test
- Location: e2e/test_rule_builder.spec.js:3:1

# Error details

```
Test timeout of 300000ms exceeded.
```

```
Error: page.waitForResponse: Test timeout of 300000ms exceeded.
```

# Page snapshot

```yaml
- generic [ref=e1]:
  - navigation [ref=e2]:
    - generic [ref=e3]:
      - link "Home" [ref=e4] [cursor=pointer]:
        - /url: /
      - button "Toggle navigation" [ref=e5]:
        - img [ref=e7]
      - generic:
        - list
      - combobox [ref=e10]
  - main [ref=e13]:
    - generic [ref=e15]:
      - generic [ref=e16]:
        - generic [ref=e17]:
          - img [ref=e18]
          - heading "Login to Frappe" [level=4] [ref=e19]
        - form [ref=e21]:
          - generic [ref=e22]:
            - generic [ref=e23]:
              - generic [ref=e24]:
                - text: Email
                - generic [ref=e25]:
                  - textbox "Email" [active] [ref=e26]:
                    - /placeholder: jane@example.com
                  - img [ref=e27]
              - generic [ref=e29]:
                - text: Password
                - generic [ref=e30]:
                  - textbox "Password" [ref=e31]:
                    - /placeholder: •••••
                  - img [ref=e32]
                  - text: Show
              - paragraph [ref=e34]:
                - link "Forgot Password?" [ref=e35] [cursor=pointer]:
                  - /url: "#forgot"
            - button "Login" [ref=e37]
            - generic [ref=e38]:
              - paragraph [ref=e39]: or
              - link "Login with Email Link" [ref=e42] [cursor=pointer]:
                - /url: "#login-with-email-link"
      - generic [ref=e43]:
        - generic [ref=e44]:
          - img [ref=e45]
          - heading "Create a Frappe Account" [level=4] [ref=e46]
        - generic [ref=e48]:
          - text: Signup Disabled
          - paragraph [ref=e49]: Signups have been disabled for this website.
          - link "Home" [ref=e51] [cursor=pointer]:
            - /url: /
      - generic [ref=e52]:
        - generic [ref=e53]:
          - img [ref=e54]
          - heading "Forgot Password" [level=4] [ref=e55]
        - form [ref=e57]:
          - generic [ref=e59]:
            - textbox "Email Address" [ref=e60]
            - img [ref=e61]
          - generic [ref=e64]:
            - button "Reset Password" [ref=e65]
            - paragraph [ref=e66]:
              - link "Back to Login" [ref=e67] [cursor=pointer]:
                - /url: "#login"
      - generic [ref=e68]:
        - generic [ref=e69]:
          - img [ref=e70]
          - heading "Login with Email Link" [level=4] [ref=e71]
        - form [ref=e73]:
          - generic [ref=e75]:
            - textbox "Email Address" [ref=e76]
            - img [ref=e77]
          - generic [ref=e80]:
            - button "Send login link" [ref=e81]
            - paragraph [ref=e82]:
              - link "Back to Login" [ref=e83] [cursor=pointer]:
                - /url: "#login"
  - contentinfo [ref=e84]:
    - generic [ref=e88]:
      - text: Built on
      - link "Frappe" [ref=e89] [cursor=pointer]:
        - /url: https://frappeframework.com?source=website_footer
```

# Test source

```ts
  1   | const { test, expect } = require('@playwright/test');
  2   |
  3   | test('Comprehensive Rule Builder E2E Test', async ({ page }) => {
  4   |   test.setTimeout(300000);
  5   |
  6   |   // 1. Login
  7   |   console.log('Navigating to login page');
  8   |   await page.goto('http://localhost:8000/login');
  9   |
  10  |   await page.waitForSelector('#login_email');
  11  |   await page.fill('#login_email', 'Administrator');
  12  |   await page.fill('#login_password', 'admin');
  13  |
  14  |   console.log('Clicking login button');
  15  |   await Promise.all([
> 16  |     page.waitForResponse(res => res.url().includes('method=login') && res.status() === 200),
      |          ^ Error: page.waitForResponse: Test timeout of 300000ms exceeded.
  17  |     page.click('button.btn-login')
  18  |   ]);
  19  |
  20  |   console.log('Login successful, waiting for Desk to load');
  21  |   await page.waitForURL('**/app**', { timeout: 60000 });
  22  |   await page.waitForSelector('.navbar, .standard-sidebar', { timeout: 60000 });
  23  |   console.log('Desk loaded, current URL:', page.url());
  24  |
  25  |   // 2. Navigate to Rule List
  26  |   console.log('Navigating to Rule list');
  27  |   await page.goto('http://localhost:8000/app/rule');
  28  |   await page.waitForLoadState('networkidle');
  29  |
  30  |   // Create New Rule
  31  |   console.log('Clicking New Rule button');
  32  |   // Frappe often has multiple New buttons, one in the list header is usually the most reliable
  33  |   const newBtn = page.locator('.page-head button.primary-action:has-text("New")');
  34  |   await newBtn.waitFor({ state: 'visible', timeout: 30000 });
  35  |   await newBtn.click();
  36  |
  37  |   console.log('On New Rule form');
  38  |   await page.waitForSelector('input[data-fieldname="rule_name"]', { timeout: 30000 });
  39  |   const ruleName = 'E2E_Test_' + Date.now();
  40  |   await page.fill('input[data-fieldname="rule_name"]', ruleName);
  41  |
  42  |   // Set Document Type
  43  |   console.log('Setting Document Type to Contact');
  44  |   const docTypeInput = page.locator('input[data-fieldname="document_type"]');
  45  |   await docTypeInput.click();
  46  |   await docTypeInput.fill('Contact');
  47  |   await page.keyboard.press('Enter');
  48  |   await page.waitForTimeout(1000);
  49  |
  50  |   // Set Trigger Event
  51  |   console.log('Setting Trigger Event to After Insert');
  52  |   await page.selectOption('select[data-fieldname="trigger_event"]', 'After Insert');
  53  |
  54  |   // Save Rule
  55  |   console.log('Saving Rule');
  56  |   await page.click('button.primary-action:has-text("Save")');
  57  |
  58  |   // Wait for Visual Builder button
  59  |   console.log('Waiting for Visual Builder button...');
  60  |   const visualBuilderBtn = page.locator('button:has-text("Visual Builder")');
  61  |   await visualBuilderBtn.waitFor({ state: 'visible', timeout: 45000 });
  62  |   await visualBuilderBtn.click();
  63  |
  64  |   // 3. Rule Builder interaction
  65  |   console.log('Entering Rule Builder');
  66  |   await page.waitForURL('**/rule-builder/**', { timeout: 30000 });
  67  |   await page.waitForSelector('.vue-flow', { timeout: 60000 });
  68  |   console.log('Rule Builder loaded');
  69  |
  70  |   // Helper to add action
  71  |   const addAction = async (type) => {
  72  |       console.log(`Adding action: ${type}`);
  73  |       const actionZones = page.locator('.fa-plus-circle');
  74  |       await actionZones.last().scrollIntoViewIfNeeded();
  75  |       await actionZones.last().click();
  76  |       await page.waitForTimeout(1000);
  77  |
  78  |       const option = page.locator(`.action-item:has-text("${type}"), text="${type}"`).first();
  79  |       await option.click();
  80  |       await page.waitForTimeout(2000);
  81  |   };
  82  |
  83  |   // Add and configure some actions
  84  |   await addAction('Assignment');
  85  |   await page.locator('.vue-flow__node:has-text("Assignment")').last().click();
  86  |   await page.waitForSelector('.action-settings-container');
  87  |   await page.fill('[data-fieldname="action_label"] input', 'Initialize Vars');
  88  |   await page.mouse.click(10, 10); // Close sidebar
  89  |
  90  |   await addAction('Notify');
  91  |   await page.locator('.vue-flow__node:has-text("Notify")').last().click();
  92  |   await page.waitForSelector('.action-settings-container');
  93  |   // Configure Notify fields if possible
  94  |   const asyncCheck = page.locator('[data-fieldname="is_async"] input[type="checkbox"]');
  95  |   if (await asyncCheck.isVisible()) await asyncCheck.check();
  96  |   await page.mouse.click(10, 10);
  97  |
  98  |   // Final Save in Builder
  99  |   console.log('Saving Rule in Builder');
  100 |   await page.click('button.btn-primary:has-text("Save Rule")');
  101 |   await page.waitForTimeout(3000);
  102 |
  103 |   await page.screenshot({ path: 'e2e/screenshots/final_result.png', fullPage: true });
  104 |   console.log('E2E Test Success!');
  105 | });
  106 |
```