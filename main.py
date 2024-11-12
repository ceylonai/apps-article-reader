import requests
from bs4 import BeautifulSoup
import json
from langchain_community.llms import Ollama
from typing import Optional, Dict, List


class ContentExtractor:
    def __init__(self, model_name: str = "llama3.2"):
        self.llm = Ollama(model=model_name)

    def get_url_content(self, url: str) -> Optional[str]:
        """Fetch and parse URL content"""
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

            # Get text content
            text = soup.get_text(separator='\n')

            # Clean text
            lines = (line.strip() for line in text.splitlines())
            text = ' '.join(chunk for chunk in lines if chunk)

            return text
        except Exception as e:
            print(f"Error fetching URL: {e}")
            return None

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
        content = self.get_url_content(url)
        if not content:
            return None

        print("Extracting title...")
        title = self.extract_title(content)

        print("Extracting keywords...")
        keywords = self.extract_keywords(content)

        print("Extracting content summary...")
        content_summary = self.extract_content_summary(content)

        print("Extracting hashtags...")
        hashtags = self.extract_hashtags(content)

        return {
            'title': title,
            'keywords': keywords,
            'content': content_summary,
            'hashtags': hashtags
        }


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
        print("\nContent Summary:", result['content'])
        print("\nHashtags:", ' '.join(result['hashtags']))
    else:
        print("Failed to extract information from the URL")


if __name__ == "__main__":
    main()