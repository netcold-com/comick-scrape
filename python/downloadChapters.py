import os
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

ROOT_FOLDER = "/var/www/html/manhwa"

def download_image(url, path):
    try:
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"    ⚠ Failed to download {url}: {e}")
        return False

def get_comick_images(url, max_attempts=3):
    for attempt in range(1, max_attempts + 1):
        print(f"  Attempt {attempt}: Loading {url}")
        options = Options()
        options.headless = True
        options.add_argument("--disable-gpu")
        driver = webdriver.Chrome(options=options)
        try:
            driver.get(url)
            time.sleep(3)  # Wait for images to load

            imgs = driver.find_elements(By.TAG_NAME, 'img')
            print(f"    Found {len(imgs)} <img> tags on the page.")

            urls = []
            for img in imgs:
                src = img.get_attribute('src')
                if src:
                    # Print every img src (comment this block out to disable)
                    # print(f"    IMG SRC: {src}")

                    # Filter only URLs from comick.pictures with valid image extensions
                    if (
                        "comick.pictures" in src.lower()
                        and re.search(r'\.(jpg|jpeg|png|webp)$', src, re.IGNORECASE)
                        and "meo3" not in src.lower()  # Exclude URLs containing meo3
                    ):
                        urls.append(src)

            if urls:
                driver.quit()
                return urls
            else:
                print("    ⚠ No valid image URLs found, retrying...")
        finally:
            driver.quit()
    print("    ⏩ Skipping (no images found after retries).")
    return []

def generate_html(chapter_number, output_dir, image_urls, prev_chap, next_chap, all_chapters):
    html_filename = f"chapter_{chapter_number:03}.html"
    html_path = os.path.join(output_dir, html_filename)

    image_dir = os.path.join(output_dir, "source", f"chapter_{chapter_number:03}")
    os.makedirs(image_dir, exist_ok=True)

    # Download images with numbering 01.jpg, 02.jpg, etc.
    for idx, img_url in enumerate(image_urls, start=1):
        img_filename = f"{idx:02}.jpg"
        img_path = os.path.join(image_dir, img_filename)
        if not os.path.exists(img_path):  # Skip already downloaded images
            print(f"    Downloading {img_url} -> {img_path}")
            download_image(img_url, img_path)

    # Prepare dropdown for all chapters
    dropdown = '<select onchange="if(this.value) window.location.href=this.value;">\n'
    dropdown += f'<option value="" selected>Jump to chapter</option>\n'
    for num, chap_file in all_chapters:
        sel = ' selected' if num == chapter_number else ''
        dropdown += f'<option value="{chap_file}"{sel}>Chapter {num}</option>\n'
    dropdown += '</select>'

    # Calculate relative path for images
    rel_image_dir = os.path.relpath(image_dir, output_dir)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write("<!DOCTYPE html>\n<html>\n<head>\n<meta charset='utf-8'>\n<style>\n")
        f.write("body { background: #000; text-align: center; color: white; font-family: Arial, sans-serif; }\n")
        f.write("img { width: 100%; max-width: 1000px; margin: 0 auto; display: block; }\n")
        f.write("a.button { display: inline-block; padding: 10px 20px; margin: 5px; background: #444; color: white; text-decoration: none; font-size: 1.2em; border-radius: 6px; }\n")
        f.write("a.button:hover { background: #666; }\n")
        f.write(".topnav { display: flex; justify-content: space-between; align-items: center; margin: 10px; }\n")
        f.write("select { font-size: 1.1em; padding: 5px; border-radius: 6px; }\n")
        f.write("</style>\n</head>\n<body>\n")

        # Top navigation bar
        f.write('<div class="topnav">\n')
        if prev_chap:
            f.write(f'<a class="button" href="{prev_chap}">⬅ Previous</a>\n')
        else:
            f.write('<span></span>\n')
        f.write(dropdown + "\n")
        if next_chap:
            f.write(f'<a class="button" href="{next_chap}">Next ➡</a>\n')
        else:
            f.write('<span></span>\n')
        f.write("</div>\n<hr>\n")

        # Images
        for idx in range(1, len(image_urls) + 1):
            img_file = f"{idx:02}.jpg"
            f.write(f'<img src="{rel_image_dir}/{img_file}" loading="lazy">\n')

        # Bottom navigation buttons
        f.write("<div class='bottomnav'>\n")
        if prev_chap:
            f.write(f'<a class="button" href="{prev_chap}">⬅ Previous</a>\n')
        if next_chap:
            f.write(f'<a class="button" href="{next_chap}">Next ➡</a>\n')
        f.write("</div>\n")

        f.write("</body>\n</html>\n")

    print(f"  ✔ Saved: {html_path}")
    return html_path

def main():
    for series_folder in sorted(os.listdir(ROOT_FOLDER)):
        series_path = os.path.join(ROOT_FOLDER, series_folder)
        if not os.path.isdir(series_path):
            continue
        chapters_file = os.path.join(series_path, "chapters.txt")
        if not os.path.isfile(chapters_file):
            print(f"⚠ No chapters.txt found for series '{series_folder}', skipping.")
            continue

        print(f"Processing series: {series_folder}")
        with open(chapters_file, "r", encoding="utf-8") as f:
            chapter_urls = [line.strip() for line in f if line.strip()]

        downloaded_file = os.path.join(series_path, "downloaded.txt")
        downloaded = set()
        if os.path.isfile(downloaded_file):
            with open(downloaded_file, "r", encoding="utf-8") as f:
                downloaded = set(line.strip() for line in f if line.strip())

        all_chapters = []
        for i, chapter_url in enumerate(chapter_urls, 1):
            all_chapters.append((i, f"chapter_{i:03}.html"))

        for i, chapter_url in enumerate(chapter_urls, 1):
            chap_id = f"chapter_{i:03}"
            if chap_id in downloaded:
                print(f"Skipping {chap_id} as it's already downloaded.")
                continue

            print(f"\n🔍 Processing {chap_id}: {chapter_url}")
            image_urls = get_comick_images(chapter_url)
            if not image_urls:
                print(f"Failed to get images for {chap_id}, skipping.")
                continue

            prev_chap = f"chapter_{i-1:03}.html" if i > 1 else None
            next_chap = f"chapter_{i+1:03}.html" if i < len(chapter_urls) else None

            try:
                html_path = generate_html(i, series_path, image_urls, prev_chap, next_chap, all_chapters)
            except Exception as e:
                print(f"Error generating HTML for {chap_id}: {e}")
                with open(os.path.join(ROOT_FOLDER, "error.log"), "a", encoding="utf-8") as errf:
                    errf.write(f"Error generating HTML for {chap_id} in {series_folder}: {e}\n")
                continue

            with open(downloaded_file, "a", encoding="utf-8") as f:
                f.write(chap_id + "\n")

if __name__ == "__main__":
    main()
