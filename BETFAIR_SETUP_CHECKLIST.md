# Betfair API Setup Checklist - Australian Version

Follow these steps in order. Check off each step as you complete it.

## ☐ Step 1: Get SSOID Token

1. ☐ Click: https://identitysso.betfair.com.au/view/login
2. ☐ Login with:
   - Username: `jryan1810`
   - Password: (your password)
3. ☐ You'll be redirected to main Betfair site
4. ☐ If not showing as logged in, login again
5. ☐ **Keep this browser window open**

---

## ☐ Step 2: Open API Visualizer

1. ☐ In a NEW tab (stay logged in), go to:
   - Try: https://developer.betfair.com/visualisers/api-ng-account-operations/
   - Or (AU): https://developer.betfair.com.au/visualisers/api-ng-account-operations/

2. ☐ Check that SSOID token is auto-populated in the visualizer
   - If not, refresh the page

---

## ☐ Step 3: Check for Existing Keys

1. ☐ In left panel, click: **`getDeveloperAppKeys`**
2. ☐ Click **`Execute`** button at bottom
3. ☐ Look at right panel:
   - If you see keys → Go to Step 5
   - If no keys → Continue to Step 4

---

## ☐ Step 4: Create New App Keys (if needed)

1. ☐ In left panel, click: **`createDeveloperAppKeys`**
2. ☐ Enter application name (must be unique):
   - Example: `HorseRacingML2025`
   - **Cannot** contain: "jryan1810" or your username
3. ☐ Click **`Execute`** at bottom

### Common Errors:
- ❌ "APP_KEY_CREATION_FAILED" → App name not unique, try different name
- ❌ Contains username → Remove "jryan1810" from app name
- ❌ Already have keys → Use `getDeveloperAppKeys` instead

---

## ☐ Step 5: Copy Your DELAYED Key

In the right panel, you'll see TWO keys created:

```
✅ Version – 1.0-Delay: MkcBqyZrD53V6A........  ← USE THIS (FREE)
   Status: Active
   Delay: Yes

❌ Version – 1.0: XyZaBcDefGhIjK........      ← DON'T USE YET
   Status: Inactive (needs activation)
   Delay: No
```

1. ☐ Find the key labeled **"Version 1.0-Delay"** or has "Delay: Yes"
2. ☐ Copy the full application key (expand column if needed)
3. ☐ It should look like: `MkcBqyZrD53V6A...` (16+ characters)

---

## ☐ Step 6: Update .env File

1. ☐ Open file: `.env`
2. ☐ Find line: `BETFAIR_APP_KEY=betfair`
3. ☐ Replace with: `BETFAIR_APP_KEY=your_actual_delayed_key_here`
4. ☐ Save the file

**Example:**
```bash
BETFAIR_APP_KEY=MkcBqyZrD53V6A1234567890
BETFAIR_USERNAME=jryan1810
BETFAIR_PASSWORD=Kn2Y9s3aRh.h8q!
```

---

## ☐ Step 7: Test Connection

1. ☐ Open terminal
2. ☐ Run: `python betfair_client.py`
3. ☐ Expected output:
   ```
   ✓ Logged in to Betfair successfully
   ✓ Found XX markets
   ✓ CONNECTION TEST SUCCESSFUL
   ```

### If you see errors:
- ❌ "Missing credentials" → Check .env has all 3 values
- ❌ "Invalid credentials" → Check username/password
- ❌ "INVALID_APP_KEY" → Check you copied the DELAYED key correctly
- ❌ Connection timeout → Check internet connection

---

## ✅ Success Checklist

Once complete, you should have:
- ☐ SSOID token obtained and auto-populated
- ☐ Application created with unique name
- ☐ DELAYED app key copied (16+ characters)
- ☐ .env file updated with real credentials
- ☐ Connection test passed

---

## 📝 Important Notes

### About the Delayed Key (FREE)
- ✅ No cost - completely free
- ✅ Data delay: 1-180 seconds (variable)
- ✅ Perfect for development and backtesting
- ✅ No volume data shown
- ✅ Doesn't require activation

### About the Live Key (£299 activation)
- ⏸️ Don't activate this yet
- ⏸️ Only use when ready to place real bets
- ⏸️ Contact automation@betfair.com.au to activate
- ⏸️ One-time fee applies

### For New Zealand Customers
If you're in NZ:
- Use VPN with Australian IP address
- Access developer sites through VPN
- .com.au endpoints required for API calls

---

## 🆘 Need Help?

**If you get stuck:**

1. **Can't access visualizer**
   - Clear browser cache
   - Try different browser (Chrome incognito)
   - Make sure you're logged into betfair.com.au

2. **App key creation fails**
   - Try different app name
   - Check name doesn't contain your username
   - Use `getDeveloperAppKeys` to check if keys already exist

3. **Still stuck?**
   - Email: automation@betfair.com.au
   - Subject: "Help creating Delayed Application Key"
   - Include your username: jryan1810

---

## 📚 Quick Reference Links

- Login for SSOID: https://identitysso.betfair.com.au/view/login
- API Visualizer: https://developer.betfair.com/visualisers/api-ng-account-operations/
- Support: automation@betfair.com.au

---

**Ready?** Start with Step 1 and work through each checkbox!
