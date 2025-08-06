import os
import re
import asyncio
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright

ROOT_DIR = "/var/www/html/manhwa"
UPDATE_FILE = os.path.join(ROOT_DIR, "update-chapters.txt")
LANGUAGE = "en"

def extract_slug(url):
    return url.rstrip("/").split("/")[-1]

def is_whole_number(chapter_str):
    try:
        return float(chapter_str).is_integer()
    except ValueError:
        return False

async def scrape_chapters_for_page(page, url):
    await page.goto(url, timeout=60000)
    await page.wait_for_load_state("networkidle")
    await page.wait_for_timeout(5000)  # Wait 5 seconds to reduce Cloudflare triggers

    previous_scroll_position = -1
    max_attempts = 50
    scroll_step = 500

    for attempt in range(max_attempts):
        scroll_position, scroll_height = await page.evaluate(
            "() => [window.scrollY, document.body.scrollHeight]"
        )
        if scroll_position == previous_scroll_position or scroll_position + scroll_step >= scroll_height:
            break
        previous_scroll_position = scroll_position
        await page.evaluate(f"window.scrollBy(0, {scroll_step})")
        await page.wait_for_timeout(300)

    chapters = await page.evaluate("""
        () => {
            const chapterList = [];
            const anchors = Array.from(document.querySelectorAll('a'));
            anchors.forEach(a => {
                const href = a.getAttribute('href');
                if (href && !href.startsWith('#') && href.includes('/comic/')) {
                    // Find upvote count inside child div with class containing 'text-sm' and 'no-link'
                    const upvoteDiv = Array.from(a.querySelectorAll('div.text-sm')).find(d => d.className.includes('no-link'));
                    let upvotes = 0;
                    if (upvoteDiv && upvoteDiv.textContent.trim()) {
                        upvotes = parseInt(upvoteDiv.textContent.trim().replace(/,/g, '')) || 0;
                    }
                    chapterList.push({ href: a.href, upvotes: upvotes });
                }
            });
            return chapterList;
        }
    """)
    return chapters

async def main():
    with open(UPDATE_FILE, "r") as f:
        lines = f.readlines()

    series_urls = []
    for line in lines[1:]:  # skip first line
        line = line.strip()
        if line == "" or line.startswith('#'):
            continue
        series_urls.append(line)

    print(f"URLs to process (excluding comments, empty lines, and skipping first line): {len(series_urls)}")
    for url in series_urls:
        print(" ->", url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Change to True for headless

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            locale="en-US",
            timezone_id="America/New_York",
            java_script_enabled=True,
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)
        page = await context.new_page()

        for series_url in series_urls:
            print(f"\nProcessing: {series_url}")
            slug = extract_slug(series_url)
            series_folder = os.path.join(ROOT_DIR, slug)
            os.makedirs(series_folder, exist_ok=True)
            chapters_file = os.path.join(series_folder, "chapters.txt")

            page_num = 1
            all_chapter_data = []
            seen_urls = set()

            while True:
                paged_url = f"{series_url}?lang={LANGUAGE}&chap-order=1&page={page_num}"
                print(f"  Loading page {page_num}...")

                try:
                    chapters = await scrape_chapters_for_page(page, paged_url)
                except Exception as e:
                    print(f"  Failed to load page {page_num} for {slug}: {e}")
                    break

                new_chapters = [ch for ch in chapters if ch['href'] not in seen_urls]
                if not new_chapters:
                    print(f"  No new chapters found on page {page_num}, stopping pagination.")
                    break

                seen_urls.update(ch['href'] for ch in new_chapters)

                for ch in new_chapters:
                    full_url = ch['href']
                    if full_url.startswith('/'):
                        full_url = "https://comick.io" + full_url

                    match = re.search(r"chapter-(\d+)(?:[^0-9]|$)", full_url)
                    if match:
                        chapter_num = int(match.group(1))
                        upvotes = ch['upvotes']
                        existing = next((item for item in all_chapter_data if item[0] == chapter_num), None)
                        if existing:
                            if upvotes > existing[2]:
                                all_chapter_data.remove(existing)
                                all_chapter_data.append((chapter_num, full_url, upvotes))
                        else:
                            all_chapter_data.append((chapter_num, full_url, upvotes))

                page_num += 1

            if not all_chapter_data:
                print(f"No valid English chapters found for {slug}")
                continue

            all_chapter_data.sort(key=lambda x: x[0])

            with open(chapters_file, "w") as f:
                for chap_num, chap_url, upvotes in all_chapter_data:
                    f.write(f"{chap_url}\n")

            print(f"Wrote {len(all_chapter_data)} chapters to {chapters_file}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
