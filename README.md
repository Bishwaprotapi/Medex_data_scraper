# MedEx Medicine Scraper

Scrape medicine data from `medex.com.bd` into SQLite, then export to CSV and a joined text file.

## What This Project Includes

- Scrapes full medicine details from brand pages (`/brands/<id>/...`)
- Stores records in SQLite (`medex_medicines.db`)
- Exports:
  - `medex_medicines.csv`
  - `medex_medicines_joined.txt` (human-readable joined output)
- Skips invalid/non-medicine links automatically
- No API key required (direct HTTP scraping)

## Installation

1. Use Python 3.11+
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Recommended Run Flow

```bash
python example_usage.py
```

The script will:

1. Scrape brand list pages and medicine detail pages directly
2. Store records in SQLite
3. Export CSV and joined file

## Cookie Configuration

The scraper supports automated cookie configuration to handle Cloudflare security challenges. Cookies are loaded in this priority order:

1. **Constructor parameter**: Pass `cookie_header` when creating `MedexScraper`
2. **Environment variable**: Set `MEDEX_COOKIE` environment variable
3. **config.json file**: Create a `config.json` file in the project directory with:
   ```json
   {
     "cookie": "your_cookie_header_here"
   }
   ```
4. **.env file**: Create a `.env` file in the project directory with:
   ```
   MEDEX_COOKIE=your_cookie_header_here
   ```

If blocked by security challenge without a configured cookie, the scraper will fail immediately with a clear error message.

### Getting the Cookie

1. Open `https://medex.com.bd` in your browser
2. Complete any security verification
3. Open Browser DevTools (F12)
4. Go to Network tab
5. Refresh the page and click any request to medex.com.bd
6. Copy the `Cookie` header from Request Headers
7. Use it in one of the configuration methods above

### Browser Cookie Loading

The scraper also attempts to load cookies from your local browser (Chrome/Edge/Firefox) automatically. To specify a browser, set `MEDEX_COOKIE_BROWSER` environment variable to one of: `chrome`, `edge`, `firefox`, `brave`, `opera`, `opera_gx`, `vivaldi`, `chromium`.

## Safe Mode (Lower Block Risk)

Default `example_usage.py` conservative mode-এ run করে:

- low request rate (`min_request_interval_seconds`)
- random delay between requests/pages
- retry with backoff

Note: কোন scraper-ই 100% block-free guarantee দিতে পারে না. Safe mode শুধু risk কমায়.

## Windows Run Command

```powershell
cd d:\iBOS\Medex
py -3 -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -u example_usage.py
```

## Programmatic Usage

```python
from medex_scraper import MedexScraper

scraper = MedexScraper(
    db_path="medex_medicines.db",
    min_request_interval_seconds=2.0,
    request_delay_range=(1.0, 2.0),
    page_delay_range=(2.0, 4.0),
    max_http_retries=3,
)

try:
    scraper.scrape_brand_list(start_page=1, max_pages=None)
    scraper.export_to_csv("medex_medicines.csv")
    scraper.export_join_file("medex_medicines_joined.txt")
finally:
    scraper.close()
```

## Author

**Bishwaprotap Ray**

- **Role**: Software Developer Intern | AI & Machine Learning Engineer
- **Education**: B.Sc. in Computer Science & Engineering (International University of Business Agriculture and Technology)
- **Specialization**: AI, Machine Learning, LLM, FastAPI, Voice Assistant Development
- **Location**: Dhaka, Bangladesh
- **Mobile**: +8801788974534
- **Email**: baburay214@gmail.com
- **LinkedIn**: [https://www.linkedin.com/in/bishwaprotap-ray/](https://www.linkedin.com/in/bishwaprotap-ray/)
- **GitHub**: [https://github.com/Bishwaprotapi](https://github.com/Bishwaprotapi)

## Notes

- Existing records are deduplicated by unique `link`.
- Keep scraping speed conservative to reduce temporary blocks/rate limits.
- If scraping returns 0 data, configure a cookie using one of the methods in the Cookie Configuration section above.
- The scraper runs in fully automated mode with no manual input prompts.
