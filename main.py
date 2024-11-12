import requests
from bs4 import BeautifulSoup
import json
from langchain_community.llms import Ollama
from typing import Optional, Dict, List
import time


class ContentExtractor:
    def __init__(self, model_name: str = "llama2"):
        self.llm = Ollama(model=model_name)

    def get_url_content(self, url: str) -> Optional[Dict[str, str]]:
        """Fetch and parse URL content, returning both raw and cleaned versions"""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get main content with formatting
            main_content = self.extract_main_content(soup)

            # Get text content for analysis
            text = soup.get_text(separator='\n')
            lines = (line.strip() for line in text.splitlines())
            cleaned_text = ' '.join(chunk for chunk in lines if chunk)

            return {
                'raw_html': str(soup),
                'main_content': main_content,
                'cleaned_text': cleaned_text
            }
        except Exception as e:
            print(f"Error fetching URL: {e}")
            return None

    def extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract the main article content while preserving important formatting"""
        # Common article container classes/IDs
        article_selectors = [
            'article',
            '[class*="article"]',
            '[class*="post"]',
            '[class*="content"]',
            'main',
            '#main-content',
            '.entry-content',
            '.post-content',
            '.article-content'
        ]

        main_content = None

        # Try each selector until we find content
        for selector in article_selectors:
            content = soup.select_one(selector)
            if content and len(content.get_text(strip=True)) > 200:
                main_content = content
                break

        if not main_content:
            # Fallback: Find the largest text block
            paragraphs = soup.find_all('p')
            if paragraphs:
                main_content = max(paragraphs, key=lambda p: len(p.get_text(strip=True)))

        if main_content:
            # Clean up the content while preserving structure
            for tag in main_content.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                tag.decompose()

            # Preserve only specific HTML tags
            allowed_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'blockquote']
            for tag in main_content.find_all():
                if tag.name not in allowed_tags:
                    tag.unwrap()

            return str(main_content)

        return ""

    def extract_full_article(self, content: str) -> str:
        """Extract and format the full article content"""
        prompt = f"""Given the following HTML content, extract and format the full article text. 
        Preserve paragraphs and headings structure. Remove any navigation, ads, or irrelevant content.
        Format the output in Markdown.

        Content: {content}

        Return the formatted article text with proper paragraph breaks and headings."""

        try:
            return self.llm.invoke(prompt).strip()
        except Exception as e:
            print(f"Error extracting full article: {e}")
            return ""

    def extract_title(self, content: str) -> str:
        """Extract title from content"""
        prompt = f"""Given the following content, extract a clear and concise title that best represents the main topic.
        Content: {content[:1000]}

        Return only the title text, without any quotes or formatting."""

        try:
            return self.llm.invoke(prompt).strip()
        except Exception as e:
            print(f"Error extracting title: {e}")
            return ""

    def extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content"""
        prompt = f"""Given the following content, extract 5-7 relevant keywords that best represent the main topics and themes.
        Content: {content[:1500]}

        Return the keywords as a comma-separated list, without any quotes or brackets."""

        try:
            response = self.llm.invoke(prompt)
            return [keyword.strip() for keyword in response.split(',')]
        except Exception as e:
            print(f"Error extracting keywords: {e}")
            return []

    def extract_content_summary(self, content: str) -> str:
        """Extract content summary"""
        prompt = f"""Given the following content, provide a brief summary in 2-3 sentences that captures the main points and key takeaways.
        Content: {content[:2000]}

        Return only the summary text, without any quotes or formatting."""

        try:
            return self.llm.invoke(prompt).strip()
        except Exception as e:
            print(f"Error extracting content summary: {e}")
            return ""

    def extract_hashtags(self, content: str) -> List[str]:
        """Extract relevant hashtags"""
        prompt = f"""Given the following content, generate 3-5 relevant hashtags that would be appropriate for social media sharing.
        Content: {content[:1000]}

        Return the hashtags as a comma-separated list, including the # symbol, without any quotes or brackets."""

        try:
            response = self.llm.invoke(prompt)
            return [hashtag.strip() for hashtag in response.split(',')]
        except Exception as e:
            print(f"Error extracting hashtags: {e}")
            return []

    def process_url(self, url: str) -> Dict:
        """Process URL and extract all information"""
        content_dict = self.get_url_content(url)
        if not content_dict:
            return None

        print("Extracting title...")
        title = self.extract_title(content_dict['cleaned_text'])

        print("Extracting keywords...")
        keywords = self.extract_keywords(content_dict['cleaned_text'])

        print("Extracting content summary...")
        content_summary = self.extract_content_summary(content_dict['cleaned_text'])

        print("Extracting hashtags...")
        hashtags = self.extract_hashtags(content_dict['cleaned_text'])

        print("Extracting full article...")
        full_article = self.extract_full_article(content_dict['main_content'])

        return {
            'title': title,
            'keywords': keywords,
            'content_summary': content_summary,
            'hashtags': hashtags,
            'full_article': full_article
        }


def save_to_file(result: Dict, url: str):
    """Save the extracted information to a file"""
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"article_extract_{timestamp}.md"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# {result['title']}\n\n")
        f.write(f"Source: {url}\n\n")
        f.write("## Keywords\n")
        f.write(", ".join(result['keywords']) + "\n\n")
        f.write("## Summary\n")
        f.write(result['content_summary'] + "\n\n")
        f.write("## Hashtags\n")
        f.write(" ".join(result['hashtags']) + "\n\n")
        f.write("## Full Article\n")
        f.write(result['full_article'])

    return filename


def main():
    # Example usage
    url = "https://read.saasdevsuite.com/how-generate-wining-sass-using-your-simple-idea/"
    extractor = ContentExtractor(model_name="llama3.2")
    result = extractor.process_url(url)

    if result:
        print("\nExtracted Information:")
        print("=====================")
        print(f"Title: {result['title']}")
        print("\nKeywords:", ', '.join(result['keywords']))
        print("\nContent Summary:", result['content_summary'])
        print("\nHashtags:", ' '.join(result['hashtags']))
        print("\nFull Article Preview (first 500 chars):")
        print(result['full_article'][:500] + "...")

        # Save to file
        filename = save_to_file(result, url)
        print(f"\nFull content saved to: {filename}")
    else:
        print("Failed to extract information from the URL")


if __name__ == "__main__":
    main()