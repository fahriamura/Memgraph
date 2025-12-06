import os
from dotenv import load_dotenv

load_dotenv()


MEMGRAPH_HOST = os.getenv("MEMGRAPH_HOST", "localhost")
MEMGRAPH_PORT = int(os.getenv("MEMGRAPH_PORT", 7687))
MEMGRAPH_USERNAME = os.getenv("MEMGRAPH_USERNAME", "")
MEMGRAPH_PASSWORD = os.getenv("MEMGRAPH_PASSWORD", "")


IRYS_SEED_URLS = [
    "https://irys.xyz",
    "https://docs.irys.xyz"
]


ENABLE_DEEP_SCRAPING = True  
MAX_SCRAPING_DEPTH = 2 
MAX_PAGES_PER_DOMAIN = 50  
MAX_TOTAL_PAGES = 100 


ALLOWED_DOMAINS = [
    "irys.xyz",
    "docs.irys.xyz",
    "explorer.irys.xyz"
]

EXCLUDED_URL_PATTERNS = [
    "/assets/",
    "/api/", 
    "javascript:",  
    "mailto:",  
    "tel:",
    ".pdf",  
    ".zip",
    ".jpg",
    ".png",
    ".gif",
    ".svg"
]
SKIP_EXTERNAL_DOMAINS = True


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


SCRAPE_INTERVAL_HOURS = 6
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
REQUEST_DELAY = 1 


DATA_DIR = "scraped_data"
CACHE_FILE = "scraper/cache.json"