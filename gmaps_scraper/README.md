---

### 5. 🗺️ [Google Maps Lead Scraper](https://adewaleolalekan.github.io/data_analytics_portfolio/gmaps_scraper/)

**Tools Used**: Python, Playwright, pandas, asyncio, openpyxl, Rich  
**Description**:  
An asynchronous web scraper that extracts structured business listings (name,
category, rating, review count, phone number, website, and address) from Google
Maps for any search query and location. Built to handle JavaScript-rendered
dynamic content via headless Chromium, with scroll-based pagination to collect
large result sets.

**Key Features**:

- 🌐 **Dynamic Content Handling**: Uses Playwright with headless Chromium to render
  and interact with JavaScript-heavy pages — going beyond what static HTML scrapers
  can access.
- 🧹 **Smart Deduplication**: Filters and deduplicates results by phone number and
  business name to ensure every exported row is a unique, contactable lead.
- 📊 **Dual Export**: Outputs timestamped `.csv` and formatted `.xlsx` files with
  auto-sized columns via openpyxl — ready for CRM import or further analysis.
- ⚡ **Async Architecture**: Built with Python's asyncio for non-blocking browser
  control and efficient pipeline execution.

**Outcome**:  
Demonstrates a complete, production-style data extraction pipeline — from browser
automation and pagination through to data cleaning and structured export.

> Built for portfolio and educational purposes.