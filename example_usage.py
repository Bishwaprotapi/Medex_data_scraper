"""
Example usage of the MedEx scraper (no API required)
"""

from medex_scraper import MedexScraper

def main():
    scraper = MedexScraper(
        max_http_retries=5,
        use_proxies=True,
        proxy_file="proxies.txt",
    )
    try:
        # Export to CSV (data already scraped)
        print("\n=== Exporting to CSV ===")
        scraper.export_to_csv('medex_medicines_final.csv')

        # Export joined text file
        print("\n=== Exporting joined file ===")
        scraper.export_join_file('medex_medicines_joined.txt')

        print("\n=== Done ===")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()
