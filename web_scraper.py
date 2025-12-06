import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Set
import time
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse
from collections import deque
import os

from config import (
    IRYS_SEED_URLS, USER_AGENT, DATA_DIR,
    ENABLE_DEEP_SCRAPING, MAX_SCRAPING_DEPTH,
    MAX_PAGES_PER_DOMAIN, MAX_TOTAL_PAGES,
    ALLOWED_DOMAINS, EXCLUDED_URL_PATTERNS,
    SKIP_EXTERNAL_DOMAINS, REQUEST_DELAY
)

class IrysScraper:
    def __init__(self, use_selenium: bool = False):
        """
        Initialize scraper dengan deep scraping support
        """
        self.use_selenium = use_selenium
        self.headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        self.driver = None
        
        # Tracking
        self.visited_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        self.pages_per_domain: Dict[str, int] = {}
        
        # Create data directory
        os.makedirs(DATA_DIR, exist_ok=True)
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL (remove fragments, trailing slashes, etc)
        """
        parsed = urlparse(url)
        # Remove fragment (#section)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        # Remove trailing slash
        if normalized.endswith('/') and normalized != f"{parsed.scheme}://{parsed.netloc}/":
            normalized = normalized[:-1]
        return normalized
    
    def _is_valid_url(self, url: str) -> bool:
        normalized = self._normalize_url(url)
        

        if normalized in self.visited_urls or normalized in self.failed_urls:
            return False
        

        parsed = urlparse(normalized)
        domain = parsed.netloc
        

        if ALLOWED_DOMAINS:
            if not any(domain.endswith(allowed) for allowed in ALLOWED_DOMAINS):
                return False
        
        
        for pattern in EXCLUDED_URL_PATTERNS:
            if pattern in normalized.lower():
                return False
        

        if domain in self.pages_per_domain:
            if self.pages_per_domain[domain] >= MAX_PAGES_PER_DOMAIN:
                return False
        

        if len(self.visited_urls) >= MAX_TOTAL_PAGES:
            return False
        
        return True
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:

        links = set() 
        for a in soup.find_all('a', href=True):
            href = a['href']
            
 
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
            
  
            if href.startswith('/'):
                full_url = urljoin(base_url, href)
            elif href.startswith('http'):
                full_url = href
            else:
                full_url = urljoin(base_url, href)
            

            normalized = self._normalize_url(full_url)
            
            if self._is_valid_url(normalized):
                links.add(normalized)
        
        return list(links)
    
    def scrape_url(self, url: str) -> Dict:
        normalized_url = self._normalize_url(url)
        
        # Skip if already visited
        if normalized_url in self.visited_urls:
            return None
        
        print(f"\n{'='*70}")
        print(f"Scraping: {url}")
        print(f"Total scraped: {len(self.visited_urls)}/{MAX_TOTAL_PAGES}")
        print('='*70)
        
        try:
            if self.use_selenium:
                self._init_selenium()
                self.driver.get(url)
                time.sleep(3)
                html_content = self.driver.page_source
            else:
                response = requests.get(url, headers=self.headers, timeout=10)
                
                # Check for errors
                if response.status_code == 404:
                    print(f"⚠ Page not found (404): {url}")
                    self.failed_urls.add(normalized_url)
                    return None
                elif response.status_code != 200:
                    print(f"⚠ HTTP {response.status_code}: {url}")
                    self.failed_urls.add(normalized_url)
                    return None
                
                response.raise_for_status()
                html_content = response.text
            
            soup = BeautifulSoup(html_content, 'lxml')
  
            data = {
                "url": url,
                "normalized_url": normalized_url,
                "timestamp": datetime.now().isoformat(),
                "title": self._extract_title(soup),
                "headings": self._extract_headings(soup),
                "paragraphs": self._extract_paragraphs(soup),
                "links": self._extract_links(soup, url) if ENABLE_DEEP_SCRAPING else [],
                "metadata": self._extract_metadata(soup)
            }
 
            if not data['paragraphs'] and not data['headings']:
                print(f"⚠ No content extracted from {url}")
                self.failed_urls.add(normalized_url)
                return None
            

            self.visited_urls.add(normalized_url)
            
           
            domain = urlparse(url).netloc
            self.pages_per_domain[domain] = self.pages_per_domain.get(domain, 0) + 1
            
            print(f"✓ Success: {data['title']}")
            print(f"  Paragraphs: {len(data['paragraphs'])}")
            print(f"  Links found: {len(data['links'])}")
            
            return data
            
        except requests.exceptions.HTTPError as e:
            print(f"✗ HTTP Error: {e}")
            self.failed_urls.add(normalized_url)
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"✗ Connection Error: {e}")
            self.failed_urls.add(normalized_url)
            return None
        except requests.exceptions.Timeout as e:
            print(f"✗ Timeout: {e}")
            self.failed_urls.add(normalized_url)
            return None
        except Exception as e:
            print(f"✗ Error: {e}")
            self.failed_urls.add(normalized_url)
            return None
    
    def scrape_with_depth(self, seed_urls: List[str] = None, max_depth: int = None) -> List[Dict]:
        if seed_urls is None:
            seed_urls = IRYS_SEED_URLS
        
        if max_depth is None:
            max_depth = MAX_SCRAPING_DEPTH
        
        print("\n" + "="*70)
        print("DEEP SCRAPING STARTED")
        print("="*70)
        print(f"Seed URLs: {len(seed_urls)}")
        print(f"Max Depth: {max_depth}")
        print(f"Max Pages: {MAX_TOTAL_PAGES}")
        print(f"Allowed Domains: {', '.join(ALLOWED_DOMAINS)}")
        print("="*70 + "\n")
        
        # Initialize queue with seed URLs at depth 0
        queue = deque()
        queued_urls = set()  # Track URLs already in queue
        
        for url in seed_urls:
            normalized = self._normalize_url(url)
            if normalized not in queued_urls:
                queue.append((normalized, 0))
                queued_urls.add(normalized)
        
        all_scraped_data = []
        
        while queue and len(self.visited_urls) < MAX_TOTAL_PAGES:
            url, depth = queue.popleft()
            
            # Check depth limit
            if depth > max_depth:
                continue
            
            # Double-check validity (might have been visited since queued)
            if not self._is_valid_url(url):
                continue
            
            # Scrape the URL
            data = self.scrape_url(url)
            
            if data:
                all_scraped_data.append(data)
                
                # Add discovered links to queue (if within depth limit)
                if depth < max_depth and ENABLE_DEEP_SCRAPING:
                    new_links = data.get('links', [])
                    valid_new_links = [link for link in new_links if link not in queued_urls]
                    
                    if valid_new_links:
                        print(f"\n  → Adding {len(valid_new_links)} new links to queue (depth {depth + 1})")
                        
                        for link in valid_new_links:
                            if self._is_valid_url(link):
                                queue.append((link, depth + 1))
                                queued_urls.add(link)
            
            # Be polite - delay between requests
            if queue:  # Don't delay after last request
                time.sleep(REQUEST_DELAY)
        
        print("\n" + "="*70)
        print("DEEP SCRAPING COMPLETED")
        print("="*70)
        print(f"Total pages scraped: {len(all_scraped_data)}")
        print(f"Total URLs visited: {len(self.visited_urls)}")
        print(f"Failed URLs: {len(self.failed_urls)}")
        print("="*70 + "\n")
        
        return all_scraped_data
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()
        
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text().strip()
        
        return "No title"
    
    def _extract_headings(self, soup: BeautifulSoup) -> List[Dict]:
        headings = []
        for level in range(1, 7):
            tags = soup.find_all(f'h{level}')
            for tag in tags:
                text = tag.get_text().strip()
                if text:
                    headings.append({
                        "level": level,
                        "text": text
                    })
        return headings
    
    def _extract_paragraphs(self, soup: BeautifulSoup) -> List[str]:
        paragraphs = []
        for p in soup.find_all('p'):
            text = p.get_text().strip()
            if text and len(text) > 20:
                paragraphs.append(text)
        return paragraphs
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict:
        metadata = {}
        

        desc_tag = soup.find('meta', attrs={'name': 'description'})
        if desc_tag and desc_tag.get('content'):
            metadata['description'] = desc_tag['content']
        

        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_tag and keywords_tag.get('content'):
            metadata['keywords'] = keywords_tag['content']
        

        og_tags = soup.find_all('meta', attrs={'property': lambda x: x and x.startswith('og:')})
        for tag in og_tags:
            prop = tag.get('property')
            content = tag.get('content')
            if prop and content:
                metadata[prop] = content
        
        return metadata
    
    def save_scraped_data(self, data: List[Dict], filename: str = None):
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{DATA_DIR}/scraped_deep_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Saved scraped data to: {filename}")
        return filename
    
    def save_statistics(self):
        stats = {
            "timestamp": datetime.now().isoformat(),
            "total_pages_scraped": len(self.visited_urls),
            "total_failed": len(self.failed_urls),
            "pages_per_domain": self.pages_per_domain,
            "visited_urls": list(self.visited_urls),
            "failed_urls": list(self.failed_urls)
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{DATA_DIR}/scraping_stats_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved statistics to: {filename}")
    
    def _init_selenium(self):
        if not self.driver:
            from selenium import webdriver
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.chrome.options import Options
            from webdriver_manager.chrome import ChromeDriverManager
            
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument(f"user-agent={USER_AGENT}")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("✓ Selenium WebDriver initialized")
    
    def close(self):
        if self.driver:
            self.driver.quit()
            print("✓ Selenium WebDriver closed")


if __name__ == "__main__":
    scraper = IrysScraper(use_selenium=False)
    

    data = scraper.scrape_with_depth(
        seed_urls=IRYS_SEED_URLS,
        max_depth=2 
    )
    
    scraper.save_scraped_data(data)
    scraper.save_statistics()
    
    scraper.close()