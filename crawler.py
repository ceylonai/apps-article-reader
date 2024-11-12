import time
from datetime import datetime
from typing import Set, List
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from content_extractor import ContentExtractor


class WebCrawler:
    def __init__(self, base_url: str, max_pages: int = 5, max_depth: int = 2):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.visited_urls: Set[str] = set()
        self.extracted_contents: List[dict] = []
        self.extractor = ContentExtractor(model_name="llama3.2")

    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and belongs to the same domain"""
        try:
            parsed = urlparse(url)
            return (
                    parsed.netloc == self.domain
                    and parsed.scheme in ['http', 'https']
                    and not url.endswith(('.pdf', '.jpg', '.png', '.gif'))
            )
        except:
            return False

    def get_links_from_page(self, url: str) -> Set[str]:
        """Extract all valid links from a page"""
        links = set()
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            for link in soup.find_all('a', href=True):
                full_url = urljoin(url, link['href'])
                if self.is_valid_url(full_url):
                    links.add(full_url)
        except Exception as e:
            print(f"Error getting links from {url}: {e}")

        return links

    def crawl_page(self, url: str, depth: int = 0) -> None:
        """Crawl a single page and extract its content"""
        if (
                depth > self.max_depth
                or url in self.visited_urls
                or len(self.visited_urls) >= self.max_pages
        ):
            return

        print(f"\nProcessing page {len(self.visited_urls) + 1}/{self.max_pages}: {url}")
        self.visited_urls.add(url)

        # Extract content
        try:
            result = self.extractor.process_url(url)
            if result:
                result['url'] = url
                result['crawl_time'] = datetime.now().isoformat()
                self.extracted_contents.append(result)
        except Exception as e:
            print(f"Error extracting content from {url}: {e}")

        # Get links and crawl them
        links = self.get_links_from_page(url)
        for link in links:
            self.crawl_page(link, depth + 1)

    def save_combined_content(self, output_file: str = None) -> str:
        """Save all extracted content to a single Markdown file"""
        if not output_file:
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            output_file = f"crawled_content_{timestamp}.md"

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Crawled Content from {self.domain}\n\n")
            f.write(f"Crawl Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Pages Crawled: {len(self.extracted_contents)}\n\n")

            for i, content in enumerate(self.extracted_contents, 1):
                f.write(f"## {i}. {content['title']}\n\n")
                f.write(f"Source: {content['url']}\n")
                f.write(f"Extracted: {content['crawl_time']}\n\n")

                f.write("### Keywords\n")
                f.write(", ".join(content['keywords']) + "\n\n")

                f.write("### Summary\n")
                f.write(content['content_summary'] + "\n\n")

                f.write("### Hashtags\n")
                f.write(" ".join(content['hashtags']) + "\n\n")

                f.write("### Full Article\n")
                f.write(content['full_article'] + "\n\n")

                if i < len(self.extracted_contents):
                    f.write("---------------------------------------------------------------\n\n")

        return output_file


def main():
    # Example usage
    base_url = "https://read.saasdevsuite.com"

    # Initialize and run crawler
    crawler = WebCrawler(
        base_url=base_url,
        max_pages=5,  # Crawl up to 5 pages
        max_depth=2  # Go 2 levels deep from the start URL
    )

    print(f"Starting crawl of {base_url}")
    start_time = time.time()

    # Start crawling from the base URL
    crawler.crawl_page(base_url)

    # Save results
    output_file = crawler.save_combined_content()

    # Print summary
    duration = time.time() - start_time
    print("\nCrawl completed!")
    print(f"Time taken: {duration:.2f} seconds")
    print(f"Pages crawled: {len(crawler.visited_urls)}")
    print(f"Content saved to: {output_file}")


if __name__ == "__main__":
    main()
