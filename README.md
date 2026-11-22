# 🧘 YogaLeadAI - Free Autonomous Lead Engine & Ad Cost Optimizer

> A client-side, zero-cost web application and automation toolkit built to slash or replace high paid ad spend (**₹50,000 / day**) for online Yoga training and Yoga Teacher Certification businesses.

---

## ⚡ The Core Problem & Solution

* **The Problem:** Your yoga startup spends **₹50,000 / day (~₹15,00,000 / month)** on Meta (Facebook/Instagram) and Google Ads. Customer Acquisition Cost (CAC) keeps climbing, ad fatigue is frequent, and delayed lead follow-ups waste up to 40% of ad spend.
* **The Solution:** Combining the strengths of two proven open-source architectures:
  1. **[`gosom/Google-Maps-Scraper`](https://github.com/gosom/Google-Maps-Scraper):** B2B directory targeting. Scrapes gyms, crossfit boxes, and fitness studios across India, UAE, UK, and the US to upsell their existing trainers with **Yoga Alliance USA Teacher Certifications (YTTC 200/300hr)**, and targets corporate offices for wellness workshops.
  2. **[`Kappaemme-git/codex-first-customer-finder-skill`](https://github.com/Kappaemme-git/codex-first-customer-finder-skill):** Social intent listening. Detects active, real-time demand signals on Reddit, forums, and communities where prospective students are asking *"Can someone recommend an affordable online yoga certification?"* or *"Need a private online yoga instructor for chronic back pain"*.
  3. **Multi-Channel AI Pitch Studio:** Drafts 1-click **WhatsApp messages**, **Cold Emails**, and **Social DMs** personalized to each prospect's exact context using free Google Gemini AI (or built-in high-converting smart templates).

---

## 🚀 How to Launch on GitHub Pages for Free (Zero Hosting Costs)

This website is engineered as a **100% client-side application** (HTML5 + Tailwind CSS + Vanilla ES6 JS). It requires **no server, no database costs, and zero build configuration**.

### Step 1: Push to your GitHub Repository
Open your terminal in this folder (`c:\Avijit\FreeLeads`) and run:
```bash
git init
git add .
git commit -m "Initial commit: YogaLeadAI Lead Engine"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

### Step 2: Turn on GitHub Pages (3 Clicks)
1. Go to your repository on GitHub (`https://github.com/YOUR_USERNAME/YOUR_REPO_NAME`).
2. Click on **Settings** (top tab) ➔ **Pages** (in the left sidebar).
3. Under **Build and deployment**:
   * **Source**: `Deploy from a branch`
   * **Branch**: Select `main` and folder `/ (root)`
4. Click **Save**.
5. Within 1–2 minutes, your live website will be published at:
   `https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/`

---

## 💻 How to Test Locally Immediately

You can test the platform right now without pushing anywhere:
1. **Option A (Instant):** Double-click `index.html` in your file explorer to open it directly in Chrome, Edge, or Brave.
2. **Option B (Local Web Server):**
   ```bash
   # Using Python:
   python -m http.server 3000
   # Then open http://localhost:3000 in your browser
   ```

---

## 🛠 Features & Architecture Breakdown

### 1. 📊 Ad Spend Replacement & ROI Simulator
* Enter your current daily ad spend (e.g. ₹50,000) and average Cost Per Lead (e.g. ₹250).
* See live calculations of how many organic leads are needed daily to shave off ₹10,000/day, ₹20,000/day, or ₹30,000/day.
* Tracks annual cash saved directly in the header.

### 2. 📍 Directory & Google Maps Explorer (B2B Leads)
* Searches live OpenStreetMap / Overpass database worldwide for **Gyms, Fitness Centers, Yoga Studios, and Tech Coworking Spaces**.
* Extracts Business Name, Address, Direct Phone Number, Website, and angles.
* **Import CSV/JSON:** Drag and drop files directly from `gosom/Google-Maps-Scraper` or custom scrapers.
* 1-Click **"Save to CRM"** or **"Draft AI Outreach"**.

### 3. 📡 Social Intent Hunter (Reddit & Community Signals)
* Listens to live public buying signals from subreddits like `r/yoga`, `r/flexibility`, `r/backpain`, `r/careerguidance`, and Twitter.
* Filters for high-intent queries (seeking recommendations, pricing comparisons, therapy inquiries).
* Direct link to original discussions to verify before reaching out.

### 4. ✨ AI Outreach Studio (WhatsApp, Email & Social)
* Generates 3 tailored pitches for each lead:
  * **WhatsApp Message:** Optimized with emojis, bullet points, and a **1-Click "Launch WhatsApp"** button (`https://wa.me/...`).
  * **Cold Email:** High-open subject line + 3-paragraph value proposition + low-friction CTA.
  * **Social / Reddit DM:** Empathetic, value-first, non-spam response answering the user's question directly.
* Powered by **Google Gemini API** (Free tier from [Google AI Studio](https://aistudio.google.com/app/apikey)) or built-in battle-tested smart templates when no key is entered.

### 5. 🗂️ Mini Lead CRM & Pipeline Tracker
* Manages your lead stages: `New` ➔ `Contacted` ➔ `Trial Booked` ➔ `Enrolled / Won` ➔ `Inactive`.
* Stores all records in browser `localStorage` (private to your browser).
* **1-Click CSV Export** to easily open leads in Excel or upload to Google Sheets.

### 6. 🐍 Offline Python Companion Scraper (`companion_scraper.py`)
* If you want to run high-volume automated background scraping locally on your laptop:
  ```bash
  python companion_scraper.py
  ```
* Scrapes Reddit search and Overpass directory into `scraped_leads.json` and `scraped_leads.csv`.
* Click **"Import CSV/JSON"** on the website to load them into your CRM with one click!

---

## 🎯 3-Phase Strategy to Safely Slash the ₹50,000/Day Ad Spend

| Phase | Action | Daily Ad Spend Target | Monthly Ad Savings |
|---|---|---|---|
| **Phase 1 (Days 1–7)** | Plug ad leakage: Connect an instant WhatsApp bot to Meta ads (contact leads within 2 minutes). Cut low-performing ad sets. Start B2B gym outreach. | Reduce from **₹50k/day** to **₹35k/day** | **₹4,50,000 / month** |
| **Phase 2 (Days 8–21)** | Ramp up Reddit intent listening + 40 daily B2B gym trainer outreach messages. Enroll 5–8 high-ticket international students ($500–$1,000 each). | Reduce to **₹20k/day** | **₹9,00,000 / month** |
| **Phase 3 (Days 22+)** | Keep ads running ONLY as a hyper-targeted retargeting machine ($15k/day) for already-engaged leads while organic inbound carries student volume. | Maintain **₹15k/day** | **₹10,50,000 / month** saved! |

---

## 📄 License & Credits
* Built with open-source reference to [`gosom/Google-Maps-Scraper`](https://github.com/gosom/Google-Maps-Scraper) and [`Kappaemme-git/codex-first-customer-finder-skill`](https://github.com/Kappaemme-git/codex-first-customer-finder-skill).
* Free to modify, deploy, and scale for your startup.
