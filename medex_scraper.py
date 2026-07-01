# =========================================================
# MEDEX FULL SCRAPER
# ALL FIELD + HTML FORMAT + RESUME SUPPORT
# =========================================================

import argparse
import json
import os
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import cloudscraper
import pandas as pd
from bs4 import BeautifulSoup, NavigableString, Tag
from dotenv import load_dotenv


class MedexScraper:

    _TAKA = "\u09f3"

    def __init__(
        self,
        *,
        max_http_retries=10,
        request_timeout_seconds=30,
        use_proxies=False,
        proxy_file="geonode-proxy-export.txt",
    ):

        # =====================================================
        # BASIC
        # =====================================================

        self.max_http_retries = int(max_http_retries)

        self.request_timeout_seconds = int(
            request_timeout_seconds
        )

        self.use_proxies = bool(use_proxies)

        self.proxy_file = proxy_file

        self.proxies = []

        self.current_proxy_index = 0

        self.script_dir = Path(__file__).resolve().parent

        self.product_list_path = (
            self.script_dir / "product_list.json"
        )

        self.csv_path = (
            self.script_dir / "medex_medicines.csv"
        )

        self.scraped_links = set()

        self._records_by_link = {}

        # =====================================================
        # LOAD ENV
        # =====================================================

        self._apply_proxy_flags_from_env_and_config()

        # =====================================================
        # LOAD PROXY
        # =====================================================

        if self.use_proxies:
            self._load_proxies()

        # =====================================================
        # SESSION
        # =====================================================

        self.session = cloudscraper.create_scraper(
            browser={
                "browser": "chrome",
                "platform": "windows",
                "mobile": False,
                "desktop": True,
            },
            delay=10,
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

        self.session.trust_env = True

        # =====================================================
        # LOAD EXISTING
        # =====================================================

        self._load_existing_csv()

        self._load_scraped_links()

        print("Medex Scraper Ready")

    # =====================================================
    # ENV
    # =====================================================

    def _apply_proxy_flags_from_env_and_config(self):

        env_file = self.script_dir / ".env"

        if env_file.exists():
            load_dotenv(env_file)

        ev = (
            os.environ.get("MEDEX_USE_PROXIES") or ""
        ).strip().lower()

        if ev in ("1", "true", "yes", "on"):
            self.use_proxies = True

        elif ev in ("0", "false", "no", "off"):
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

                    if line.startswith("#"):
                        continue

                    parts = line.split(":")

                    if len(parts) < 4:
                        continue

                    host = parts[0]
                    port = parts[1]
                    username = parts[2]
                    password = ":".join(parts[3:])

                    proxy_url = (
                        f"http://{username}:{password}"
                        f"@{host}:{port}"
                    )

                    self.proxies.append(
                        {
                            "http": proxy_url,
                            "https": proxy_url,
                        }
                    )

            print(
                f"Loaded {len(self.proxies)} proxies"
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
    # LOAD CSV
    # =====================================================

    def _load_existing_csv(self):

        if not self.csv_path.exists():
            return

        try:

            df = pd.read_csv(self.csv_path)

            if "link" not in df.columns:
                return

            for _, row in df.iterrows():

                link = str(
                    row.get("link", "")
                ).strip()

                if link:
                    self.scraped_links.add(link)

            print(
                f"Loaded "
                f"{len(self.scraped_links)} "
                f"links from CSV"
            )

        except Exception as e:

            print(f"CSV load error: {e}")

    # =====================================================
    # LOAD JSON
    # =====================================================

    def _load_scraped_links(self):

        try:

            if not self.product_list_path.exists():

                with open(
                    self.product_list_path,
                    "w",
                    encoding="utf-8",
                ) as f:

                    json.dump([], f)

                return

            if (
                self.product_list_path.stat().st_size
                == 0
            ):

                with open(
                    self.product_list_path,
                    "w",
                    encoding="utf-8",
                ) as f:

                    json.dump([], f)

                return

            with open(
                self.product_list_path,
                "r",
                encoding="utf-8",
            ) as f:

                content = f.read().strip()

                if not content:
                    return

                data = json.loads(content)

            if not isinstance(data, list):
                return

            for item in data:

                if isinstance(item, dict):

                    link = item.get("link")

                    if link:
                        self.scraped_links.add(link)

                elif isinstance(item, str):

                    self.scraped_links.add(item)

            print(
                f"Loaded "
                f"{len(self.scraped_links)} "
                f"links from JSON"
            )

        except Exception as e:

            print(f"JSON load error: {e}")

    # =====================================================
    # SAVE LINK
    # =====================================================

    def save_link_to_json(self, link):

        try:

            data = []

            if self.product_list_path.exists():

                with open(
                    self.product_list_path,
                    "r",
                    encoding="utf-8",
                ) as f:

                    content = f.read().strip()

                    if content:
                        data = json.loads(content)

            if not isinstance(data, list):
                data = []

            existing = set()

            for item in data:

                if isinstance(item, dict):

                    existing.add(item.get("link"))

                elif isinstance(item, str):

                    existing.add(item)

            if link not in existing:

                data.append({"link": link})

                with open(
                    self.product_list_path,
                    "w",
                    encoding="utf-8",
                ) as f:

                    json.dump(
                        data,
                        f,
                        indent=2,
                        ensure_ascii=False,
                    )

                print(f"Saved link: {link}")

        except Exception as e:

            print(f"Save JSON error: {e}")

    # =====================================================
    # REQUEST
    # =====================================================

    def _fetch_html(self, url):

        last_exc = None

        for attempt in range(
            self.max_http_retries
        ):

            try:

                proxy = None

                if self.use_proxies:
                    proxy = self._get_next_proxy()

                response = self.session.get(
                    url,
                    timeout=self.request_timeout_seconds,
                    allow_redirects=True,
                    proxies=proxy,
                )

                response.raise_for_status()

                return response.text

            except Exception as e:

                last_exc = e

                print(
                    f"Retry "
                    f"{attempt + 1}/"
                    f"{self.max_http_retries}"
                )

        raise RuntimeError(
            f"Failed to fetch {url} | {last_exc}"
        )

    def _load_soup(self, url):

        html = self._fetch_html(url)

        return BeautifulSoup(html, "lxml")

    # =====================================================
    # URL VALIDATION
    # =====================================================

    def _is_brand_detail_url(self, url):

        try:

            parsed = urlparse(url)

            return re.match(
                r"^/brands/\d+(/|$)",
                parsed.path or "",
            ) is not None

        except Exception:
            return False

    # =====================================================
    # EXTRACT LINKS
    # =====================================================

    def _extract_medicine_urls_from_brand_list(
        self,
        soup,
    ):

        urls = []

        seen = set()

        pattern = re.compile(
            r"^/brands/\d+(/|$)"
        )

        for a in soup.find_all("a", href=True):

            href = (
                a.get("href") or ""
            ).strip()

            if not href:
                continue

            full = urljoin(
                "https://medex.com.bd",
                href,
            )

            parsed = urlparse(full)

            if parsed.netloc != "medex.com.bd":
                continue

            if not pattern.match(parsed.path):
                continue

            full = full.split("#")[0]

            if full not in seen:

                seen.add(full)

                urls.append(full)

                self.save_link_to_json(full)

        return urls

    # =====================================================
    # PRICE
    # =====================================================

    def _extract_price(self, soup):

        unit_price = None
        strip_price = None

        # =================================================
        # UNIT PRICE
        # =================================================

        unit_div = soup.find(
            "div",
            class_=lambda c:
            c
            and "package-container" in str(c)
            and "mt-5" in str(c)
            and "mb-5" in str(c)
        )

        if unit_div:

            text = unit_div.get_text(
                " ",
                strip=True,
            )

            m = re.search(
                r"৳\s*([\d,.]+)",
                text,
            )

            if m:
                unit_price = m.group(1)

        # =================================================
        # STRIP PRICE
        # =================================================

        strip_div = soup.find(
            class_=lambda c:
            c
            and "pack-size-info" in str(c)
        )

        if strip_div:

            text = strip_div.get_text(
                " ",
                strip=True,
            )

            m = re.search(
                r"৳\s*([\d,.]+)",
                text,
            )

            if m:
                strip_price = m.group(1)

        return unit_price, strip_price

    # =====================================================
    # DESCRIPTION HTML
    # =====================================================

    def _extract_section_html(
        self,
        soup,
        section_id,
    ):

        try:

            section = soup.find(
                "div",
                id=section_id,
            )

            if not section:
                return None

            body = section.find_next_sibling(
                "div",
                class_="ac-body",
            )

            if not body:
                return None

            final_html = "<div>"

            for child in body.children:

                # =========================================
                # TEXT NODE
                # =========================================

                if isinstance(
                    child,
                    NavigableString,
                ):

                    text = str(child).strip()

                    if text:
                        final_html += (
                            f"<p>{text}</p>"
                        )

                # =========================================
                # TAG NODE
                # =========================================

                elif isinstance(child, Tag):

                    tag_name = child.name

                    # -------------------------------------
                    # P
                    # -------------------------------------

                    if tag_name == "p":

                        final_html += str(child)

                    # -------------------------------------
                    # UL / OL
                    # -------------------------------------

                    elif tag_name in [
                        "ul",
                        "ol",
                    ]:

                        final_html += (
                            f"<p>{str(child)}</p>"
                        )

                    # -------------------------------------
                    # TABLE
                    # -------------------------------------

                    elif tag_name == "table":

                        final_html += (
                            f"<p>{str(child)}</p>"
                        )

                    # -------------------------------------
                    # DIV
                    # -------------------------------------

                    elif tag_name == "div":

                        inner = child.get_text(
                            " ",
                            strip=True,
                        )

                        if inner:

                            final_html += (
                                f"<p>{inner}</p>"
                            )

                    # -------------------------------------
                    # OTHER
                    # -------------------------------------

                    else:

                        txt = child.get_text(
                            " ",
                            strip=True,
                        )

                        if txt:

                            final_html += (
                                f"<p>{txt}</p>"
                            )

            final_html += "</div>"

            return final_html

        except Exception as e:

            print(
                f"Section extract error: {e}"
            )

            return None

    # =====================================================
    # SCRAPE PAGE
    # =====================================================

    def scrape_medicine_page(self, url):

        try:

            if not self._is_brand_detail_url(url):

                print(f"Invalid URL: {url}")

                return None

            # =================================================
            # SKIP
            # =================================================

            if url in self.scraped_links:

                print(
                    f"Already scraped: {url}"
                )

                return None

            print(f"Scraping: {url}")

            soup = self._load_soup(url)

            medicine_data = {
                "brand_name": None,
                "generic_name": None,
                "type": None,
                "unit_price": None,
                "strip_price": None,
                "manufacturer": None,
                "figure_link": None,
                "link": url,
                "indications": None,
                "pharmacology": None,
                "dosage_administration": None,
                "interaction": None,
                "contraindications": None,
                "side_effects": None,
                "pregnancy_lactation": None,
                "precautions_warnings": None,
                "use_special_populations": None,
                "overdose_effects": None,
                "therapeutic_class": None,
                "storage_conditions": None,
                "quick_tips": None,
            }

            # =================================================
            # BRAND
            # =================================================

            brand_elem = soup.find("h1")

            if brand_elem:

                medicine_data["brand_name"] = (
                    brand_elem.get_text(
                        strip=True
                    )
                )

            # =================================================
            # GENERIC
            # =================================================

            generic_elem = soup.find(
                "div",
                title="Generic Name",
            )

            if generic_elem:

                a = generic_elem.find("a")

                if a:

                    medicine_data[
                        "generic_name"
                    ] = a.get_text(
                        strip=True
                    )

            # =================================================
            # TYPE
            # =================================================

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

            # =================================================
            # MANUFACTURER
            # =================================================

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

            # =================================================
            # IMAGE
            # =================================================

            img = soup.find(
                "a",
                class_="mp-trigger",
            )

            if img and img.get("href"):

                medicine_data[
                    "figure_link"
                ] = img.get("href")

            # =================================================
            # PRICE
            # =================================================

            unit_price, strip_price = (
                self._extract_price(soup)
            )

            medicine_data[
                "unit_price"
            ] = unit_price

            medicine_data[
                "strip_price"
            ] = strip_price

            # =================================================
            # SECTION MAP
            # =================================================

            section_map = {
                "indications": "indications",
                "pharmacology": "mode_of_action",
                "dosage_administration": "dosage",
                "interaction": "interaction",
                "contraindications": "contraindications",
                "side_effects": "side_effects",
                "pregnancy_lactation": "pregnancy_cat",
                "precautions_warnings": "precautions",
                "use_special_populations": "pediatric_uses",
                "overdose_effects": "overdose_effects",
                "therapeutic_class": "drug_classes",
                "storage_conditions": "storage_conditions",
                "quick_tips": "quick_tips",
            }

            for key, html_id in section_map.items():

                medicine_data[key] = (
                    self._extract_section_html(
                        soup,
                        html_id,
                    )
                )

            # =================================================
            # SAVE
            # =================================================

            self.scraped_links.add(url)

            self.save_link_to_json(url)

            return medicine_data

        except Exception as e:

            print(f"Scrape error: {e}")

            return None

    # =====================================================
    # UPSERT
    # =====================================================

    def upsert_record(self, medicine_data):

        if not medicine_data:
            return False

        link = medicine_data.get("link")

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

                old_rows = old_df.to_dict(
                    "records"
                )

            except Exception:
                pass

        combined = {}

        # OLD
        for row in old_rows:

            link = str(
                row.get("link", "")
            ).strip()

            if link:
                combined[link] = row

        # NEW
        for row in rows:

            link = str(
                row.get("link", "")
            ).strip()

            if link:
                combined[link] = row

        final_rows = list(
            combined.values()
        )

        columns = [
            "brand_name",
            "generic_name",
            "type",
            "unit_price",
            "strip_price",
            "manufacturer",
            "figure_link",
            "link",
            "indications",
            "pharmacology",
            "dosage_administration",
            "interaction",
            "contraindications",
            "side_effects",
            "pregnancy_lactation",
            "precautions_warnings",
            "use_special_populations",
            "overdose_effects",
            "therapeutic_class",
            "storage_conditions",
            "quick_tips",
        ]

        df = pd.DataFrame(
            final_rows,
            columns=columns,
        )

        df.to_csv(
            self.csv_path,
            index=False,
            encoding="utf-8",
        )

        print(
            f"CSV Updated | "
            f"Total Rows: {len(df)}"
        )

    # =====================================================
    # SCRAPE LIST
    # =====================================================

    def scrape_brand_list(self):

        page = 1

        while True:

            try:

                print(
                    f"\n========== "
                    f"PAGE {page} "
                    f"=========="
                )

                url = (
                    "https://medex.com.bd/"
                    f"brands/?page={page}"
                )

                soup = self._load_soup(url)

                medicine_urls = (
                    self._extract_medicine_urls_from_brand_list(
                        soup
                    )
                )

                print(
                    f"Found "
                    f"{len(medicine_urls)} "
                    f"medicine links"
                )

                if not medicine_urls:

                    print(
                        "No more medicine links"
                    )

                    break

                for med_url in medicine_urls:

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

                page += 1

            except Exception as e:

                print(
                    f"Page scrape error: {e}"
                )

                break

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
        use_proxies=True,
        proxy_file=args.proxy_file,
    )

    scraper.scrape_brand_list()

    scraper.close()