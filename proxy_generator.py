# =========================================================
# MEDEX SCRAPER
# SCRAPE ONLY UNSCRAPED LINKS
# NO DUPLICATE CSV
# NO JSON WRITE
# =========================================================

import argparse
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import cloudscraper
import pandas as pd
from bs4 import BeautifulSoup
from dotenv import load_dotenv


class MedexScraper:

    def __init__(
        self,
        *,
        max_http_retries=5,
        request_timeout_seconds=30,
        use_proxies=False,
        proxy_file="geonode-proxy-export.txt",
    ):

        self.max_http_retries = int(
            max_http_retries
        )

        self.request_timeout_seconds = int(
            request_timeout_seconds
        )

        self.use_proxies = bool(
            use_proxies
        )

        self.proxy_file = proxy_file

        self.proxies = []

        self.current_proxy_index = 0

        self.script_dir = (
            Path(__file__).resolve().parent
        )

        self.product_list_path = (
            self.script_dir / "product_list.json"
        )

        self.csv_path = (
            self.script_dir / "medex_medicines.csv"
        )

        # ==========================================
        # IMPORTANT
        # ==========================================

        self.csv_links = set()

        self.product_links = set()

        self._records_by_link = {}

        self._apply_proxy_flags_from_env_and_config()

        if self.use_proxies:
            self._load_proxies()

        # ==========================================
        # SESSION
        # ==========================================

        self.session = (
            cloudscraper.create_scraper(
                browser={
                    "browser": "chrome",
                    "platform": "windows",
                    "mobile": False,
                    "desktop": True,
                },
                delay=10,
            )
        )

        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/124.0.0.0 "
                    "Safari/537.36"
                )
            }
        )

        # ==========================================
        # LOAD DATA
        # ==========================================

        self._load_existing_csv()

        self._load_product_links()

        print("\nMedex Scraper Ready")

    # =====================================================
    # ENV
    # =====================================================

    def _apply_proxy_flags_from_env_and_config(
        self
    ):

        env_file = self.script_dir / ".env"

        if env_file.exists():
            load_dotenv(env_file)

        ev = (
            os.environ.get(
                "MEDEX_USE_PROXIES"
            )
            or ""
        ).strip().lower()

        if ev in (
            "1",
            "true",
            "yes",
            "on",
        ):
            self.use_proxies = True

        elif ev in (
            "0",
            "false",
            "no",
            "off",
        ):
            self.use_proxies = False

    # =====================================================
    # PROXY
    # =====================================================

    def _load_proxies(self):

        try:

            with open(
                self.proxy_file,
                "r",
                encoding="utf-8",
            ) as f:

                for line in f:

                    line = line.strip()

                    if not line:
                        continue

                    parts = line.split(":")

                    if len(parts) < 4:
                        continue

                    host = parts[0]
                    port = parts[1]
                    username = parts[2]
                    password = ":".join(
                        parts[3:]
                    )

                    proxy_url = (
                        f"http://"
                        f"{username}:{password}"
                        f"@{host}:{port}"
                    )

                    self.proxies.append(
                        {
                            "http": proxy_url,
                            "https": proxy_url,
                        }
                    )

            print(
                f"Loaded "
                f"{len(self.proxies)} proxies"
            )

        except Exception as e:

            print(f"Proxy load error: {e}")

    def _get_next_proxy(self):

        if not self.proxies:
            return None

        proxy = self.proxies[
            self.current_proxy_index
        ]

        self.current_proxy_index = (
            self.current_proxy_index + 1
        ) % len(self.proxies)

        return proxy

    # =====================================================
    # LOAD CSV LINKS
    # =====================================================

    def _load_existing_csv(self):

        if not self.csv_path.exists():
            return

        try:

            df = pd.read_csv(
                self.csv_path
            )

            if "link" not in df.columns:
                return

            for _, row in df.iterrows():

                link = str(
                    row.get("link", "")
                ).strip()

                if (
                    link
                    and link != "nan"
                ):
                    self.csv_links.add(
                        link
                    )

            print(
                f"Loaded "
                f"{len(self.csv_links)} "
                f"scraped CSV links"
            )

        except Exception as e:

            print(f"CSV load error: {e}")

    # =====================================================
    # LOAD JSON LINKS
    # =====================================================

    def _load_product_links(self):

        try:

            if not self.product_list_path.exists():

                print(
                    "product_list.json not found"
                )

                return

            with open(
                self.product_list_path,
                "r",
                encoding="utf-8",
            ) as f:

                data = json.load(f)

            if not isinstance(data, list):
                return

            for item in data:

                if isinstance(item, dict):

                    link = item.get(
                        "link"
                    )

                    if link:
                        self.product_links.add(
                            link
                        )

                elif isinstance(item, str):

                    self.product_links.add(
                        item
                    )

            print(
                f"Loaded "
                f"{len(self.product_links)} "
                f"product links"
            )

        except Exception as e:

            print(f"JSON load error: {e}")

    # =====================================================
    # FETCH
    # =====================================================

    def _fetch_html(self, url):

        last_exc = None

        for attempt in range(
            self.max_http_retries
        ):

            try:

                proxy = None

                if (
                    self.use_proxies
                    and self.proxies
                ):
                    proxy = (
                        self._get_next_proxy()
                    )

                response = self.session.get(
                    url,
                    timeout=(
                        self.request_timeout_seconds
                    ),
                    proxies=proxy,
                )

                response.raise_for_status()

                html = response.text

                # ======================================
                # SECURITY CHECK DETECT
                # ======================================

                if (
                    "security check"
                    in html.lower()
                ):

                    print(
                        "Security Check Found"
                    )

                    time.sleep(5)

                    continue

                return html

            except Exception as e:

                last_exc = e

                print(
                    f"Retry "
                    f"{attempt + 1}/"
                    f"{self.max_http_retries}"
                )

                print(e)

                time.sleep(3)

        return None

    def _load_soup(self, url):

        html = self._fetch_html(url)

        if not html:
            return None

        return BeautifulSoup(
            html,
            "lxml",
        )

    # =====================================================
    # URL CHECK
    # =====================================================

    def _is_brand_detail_url(
        self,
        url,
    ):

        try:

            parsed = urlparse(url)

            return (
                re.match(
                    r"^/brands/\d+(/|$)",
                    parsed.path or "",
                )
                is not None
            )

        except Exception:
            return False

    # =====================================================
    # SCRAPE PAGE
    # =====================================================

    def scrape_medicine_page(
        self,
        url,
    ):

        try:

            # ==========================================
            # SKIP IF CSV ALREADY HAS IT
            # ==========================================

            if url in self.csv_links:

                print(
                    f"Already Scraped: {url}"
                )

                return None

            print(f"Scraping: {url}")

            soup = self._load_soup(url)

            if soup is None:
                return None

            brand_elem = soup.find("h1")

            if not brand_elem:
                return None

            brand_name = (
                brand_elem.get_text(
                    strip=True
                )
            )

            # ==========================================
            # DOUBLE SECURITY CHECK
            # ==========================================

            if (
                "security check"
                in brand_name.lower()
            ):
                return None

            medicine_data = {
                "brand_name": brand_name,
                "generic_name": None,
                "type": None,
                "unit_price": None,
                "strip_price": None,
                "manufacturer": None,
                "figure_link": None,
                "link": url,
            }

            generic_elem = soup.find(
                "div",
                title="Generic Name",
            )

            if generic_elem:

                a = generic_elem.find(
                    "a"
                )

                if a:

                    medicine_data[
                        "generic_name"
                    ] = a.get_text(
                        strip=True
                    )

            type_elem = soup.find(
                "small",
                class_="h1-subtitle",
            )

            if type_elem:

                medicine_data["type"] = (
                    type_elem.get_text(
                        strip=True
                    )
                )

            company = soup.find(
                "div",
                title="Manufactured by",
            )

            if company:

                a = company.find("a")

                if a:

                    medicine_data[
                        "manufacturer"
                    ] = a.get_text(
                        strip=True
                    )

            img = soup.find(
                "a",
                class_="mp-trigger",
            )

            if (
                img
                and img.get("href")
            ):

                medicine_data[
                    "figure_link"
                ] = img.get("href")

            self.csv_links.add(url)

            return medicine_data

        except Exception as e:

            print(
                f"Scrape Error: {e}"
            )

            return None

    # =====================================================
    # UPSERT
    # =====================================================

    def upsert_record(
        self,
        medicine_data,
    ):

        if not medicine_data:
            return False

        link = medicine_data.get(
            "link"
        )

        if not link:
            return False

        self._records_by_link[
            link
        ] = medicine_data

        return True

    # =====================================================
    # EXPORT CSV
    # =====================================================

    def export_to_csv(self):

        rows = list(
            self._records_by_link.values()
        )

        old_rows = []

        if self.csv_path.exists():

            try:

                old_df = pd.read_csv(
                    self.csv_path
                )

                old_rows = (
                    old_df.to_dict(
                        "records"
                    )
                )

            except Exception:
                pass

        combined = {}

        for row in old_rows:

            link = str(
                row.get("link", "")
            ).strip()

            if link:
                combined[link] = row

        for row in rows:

            link = str(
                row.get("link", "")
            ).strip()

            if link:
                combined[link] = row

        final_rows = list(
            combined.values()
        )

        df = pd.DataFrame(
            final_rows
        )

        df.to_csv(
            self.csv_path,
            index=False,
            encoding="utf-8",
        )

        print(
            f"CSV Updated | "
            f"{len(df)} rows"
        )

    # =====================================================
    # MAIN SCRAPER
    # =====================================================

    def scrape_brand_list(self):

        pending_links = []

        # ==========================================
        # ONLY UNSCRAPED LINKS
        # ==========================================

        for link in self.product_links:

            if link not in self.csv_links:

                pending_links.append(
                    link
                )

        print(
            f"\nPending Links: "
            f"{len(pending_links)}"
        )

        for index, med_url in enumerate(
            pending_links,
            start=1,
        ):

            try:

                print(
                    f"\n[{index}/"
                    f"{len(pending_links)}]"
                )

                data = (
                    self.scrape_medicine_page(
                        med_url
                    )
                )

                if data:

                    self.upsert_record(
                        data
                    )

                    self.export_to_csv()

            except Exception as e:

                print(
                    f"Scrape Failed: {e}"
                )

    # =====================================================
    # CLOSE
    # =====================================================

    def close(self):
        pass


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--proxy-file",
        default="geonode-proxy-export.txt",
    )

    args = parser.parse_args()

    scraper = MedexScraper(
        use_proxies=False,
        proxy_file=args.proxy_file,
    )

    scraper.scrape_brand_list()

    scraper.close()