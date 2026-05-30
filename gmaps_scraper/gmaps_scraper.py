"""
Google Maps Lead Scraper
Scrapes business listings (name, address, phone, website, rating)
for any search query and location.

Usage:
  python gmaps_scraper.py --query "restaurants" --location "Lagos Nigeria" --limit 50
"""

import asyncio
import argparse
import time
import re
import pandas as pd
from datetime import datetime
from playwright.async_api import async_playwright
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


async def scrape_google_maps(query: str, location: str, limit: int = 50):
    """Scrape business listings from Google Maps."""
    
    search_term = f"{query} in {location}"
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="America/New_York",
        )
        page = await context.new_page()

        console.print(f"\n[bold green]Searching:[/bold green] {search_term}")
        
        # Navigate to Google Maps search
        url = f"https://www.google.com/maps/search/{search_term.replace(' ', '+')}"
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5)

        # Find the results sidebar
        sidebar = page.locator('div[role="feed"]')

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(
                f"[cyan]Collecting up to {limit} listings...", total=limit
            )

            collected = 0
            last_count = 0
            no_change_streak = 0

            seen_urls = set()

            while collected < limit:
                listings = await page.locator(
                    'a[href*="/maps/place/"]'
                ).all()

                current_count = len(listings)

                if current_count == last_count:
                    no_change_streak += 1
                    if no_change_streak >= 5:
                        console.print(
                            "\n[yellow]No more results found.[/yellow]"
                        )
                        break
                else:
                    no_change_streak = 0
                    last_count = current_count

                await page.evaluate(
                    "document.querySelector('div[role=\"feed\"]')"
                    ".scrollBy(0, 1000)"
                )
                await asyncio.sleep(1.5)

                # Count only unique URLs so limit means unique results
                unique_urls = set()
                for listing in listings:
                    href = await listing.get_attribute("href")
                    if href:
                        unique_urls.add(href.split("?")[0])

                seen_urls = unique_urls
                collected = min(len(seen_urls), limit)
                progress.update(
                    task,
                    completed=collected,
                    description=(
                        f"[cyan]Found {len(seen_urls)} unique "
                        f"(scrolling for {limit})..."
                    )
                )

            # Now extract details from each listing
            progress.update(task, description="[cyan]Extracting details...")

            listings = await page.locator(
                'a[href*="/maps/place/"]'
            ).all()

            # Deduplicate listings by URL before extracting
            seen = set()
            unique_listings = []
            for listing in listings:
                href = await listing.get_attribute("href")
                if href:
                    key = href.split("?")[0]
                    if key not in seen:
                        seen.add(key)
                        unique_listings.append(listing)

            # If Google ran dry, report honestly
            if len(unique_listings) < limit:
                console.print(
                    f"\n[yellow]Google Maps only has "
                    f"{len(unique_listings)} unique listings "
                    f"for this search. Extracting all of them.[/yellow]"
                )
            unique_listings = unique_listings[:limit]
            console.print(
                f"\n[green]Unique listings to extract: "
                f"{len(unique_listings)}[/green]"
            )

            for i, listing in enumerate(unique_listings):
                try:
                    await listing.click()
                    await asyncio.sleep(2)

                    data = {}

                    # Business name
                    try:
                        name_el = page.locator(
                            'h1.DUwDvf, h1[class*="fontHeadlineLarge"]'
                        ).first
                        data["name"] = await name_el.inner_text(timeout=3000)
                    except Exception:
                        data["name"] = ""

                    # Rating
                    try:
                        rating_el = page.locator(
                            'span[aria-hidden="true"].ceNzKf, '
                            'div.F7nice span[aria-hidden]'
                        ).first
                        data["rating"] = await rating_el.inner_text(
                            timeout=2000
                        )
                    except Exception:
                        data["rating"] = ""

                    # Review count
                    try:
                        reviews_el = page.locator(
                            'span[aria-label*="review"]'
                        ).first
                        label = await reviews_el.get_attribute(
                            "aria-label", timeout=2000
                        )
                        data["reviews"] = re.sub(r"[^\d]", "", label or "")
                    except Exception:
                        data["reviews"] = ""

                    # Address
                    try:
                        addr_el = page.locator(
                            'button[data-item-id="address"] div.fontBodyMedium'
                        ).first
                        data["address"] = await addr_el.inner_text(
                            timeout=2000
                        )
                    except Exception:
                        data["address"] = ""

                    # Phone
                    try:
                        phone_el = page.locator(
                            'button[data-item-id*="phone"] div.fontBodyMedium'
                        ).first
                        data["phone"] = await phone_el.inner_text(
                            timeout=2000
                        )
                    except Exception:
                        data["phone"] = ""

                    # Website
                    try:
                        web_el = page.locator(
                            'a[data-item-id="authority"]'
                        ).first
                        data["website"] = await web_el.get_attribute(
                            "href", timeout=2000
                        )
                    except Exception:
                        data["website"] = ""

                    # Category
                    try:
                        cat_el = page.locator(
                            'button.DkEaL, span[jsaction*="category"]'
                        ).first
                        data["category"] = await cat_el.inner_text(
                            timeout=2000
                        )
                    except Exception:
                        data["category"] = ""

                    data["source"] = "Google Maps"
                    data["scraped_at"] = datetime.now().strftime(
                        "%Y-%m-%d %H:%M"
                    )

                    if data.get("name"):
                        results.append(data)
                        progress.update(
                            task,
                            description=(
                                f"[cyan]Extracted {len(results)}: "
                                f"{data['name'][:40]}"
                            )
                        )

                except Exception as e:
                    console.print(f"\n[red]Error on listing {i+1}: {e}[/red]")
                    continue

        await browser.close()

    return results


def export_results(results: list, query: str, location: str):
    """Export results to CSV and Excel."""
    
    if not results:
        console.print("[red]No results to export.[/red]")
        return

    df = pd.DataFrame(results)

    # Deduplicate by phone number (primary) then by name (secondary)
    before = len(df)
    df = df[df["phone"] != ""]  # only keep rows with a phone number
    df = df.drop_duplicates(subset=["phone"], keep="first")
    df = df.drop_duplicates(subset=["name"], keep="first")
    dupes_removed = before - len(df)

    # Clean up columns
    column_order = [
        "name", "category", "rating", "reviews",
        "phone", "website", "address", "source", "scraped_at"
    ]
    df = df.reindex(columns=column_order)
    df = df.fillna("")

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    slug = f"{query}_{location}".replace(" ", "_").lower()[:40]
    filename = f"leads_{slug}_{timestamp}"

    # Export CSV
    csv_path = f"{filename}.csv"
    df.to_csv(csv_path, index=False)

    # Export Excel with formatting
    xlsx_path = f"{filename}.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Leads", index=False)
        ws = writer.sheets["Leads"]

        # Auto-size columns
        for col in ws.columns:
            max_len = max(
                len(str(cell.value or "")) for cell in col
            )
            ws.column_dimensions[col[0].column_letter].width = min(
                max_len + 4, 50
            )

    # Print summary table
    table = Table(title=f"\nResults Summary — {query} in {location}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total leads", str(len(df)))
    table.add_row(
        "With phone numbers",
        str(df[df["phone"] != ""].shape[0])
    )
    table.add_row(
        "With websites",
        str(df[df["website"] != ""].shape[0])
    )
    table.add_row(
        "Average rating",
        str(
            round(
                pd.to_numeric(df["rating"], errors="coerce").mean(), 2
            )
        )
    )
    table.add_row("Duplicates removed", str(dupes_removed))
    table.add_row("CSV saved to", csv_path)
    table.add_row("Excel saved to", xlsx_path)

    console.print(table)


async def main():
    parser = argparse.ArgumentParser(
        description="Google Maps Lead Scraper"
    )
    parser.add_argument(
        "--query",
        required=True,
        help='Business type to search (e.g. "restaurants")'
    )
    parser.add_argument(
        "--location",
        required=True,
        help='Location (e.g. "Lagos Nigeria")'
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max number of listings to collect (default: 50)"
    )
    args = parser.parse_args()

    console.print(
        "[bold]Google Maps Lead Scraper[/bold]",
        style="bold blue"
    )
    console.print(f"Query: [green]{args.query}[/green]")
    console.print(f"Location: [green]{args.location}[/green]")
    console.print(f"Limit: [green]{args.limit}[/green]\n")

    results = await scrape_google_maps(
        args.query, args.location, args.limit
    )
    export_results(results, args.query, args.location)


if __name__ == "__main__":
    asyncio.run(main())
