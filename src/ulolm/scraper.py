import urllib.request
import urllib.parse
import re
from html.parser import HTMLParser
from typing import List, Dict, Any

class TextExtractParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.recording = False
        self.text_chunks = []
        self.ignore_tags = {'script', 'style', 'header', 'footer', 'nav', 'noscript', 'head', 'iframe'}

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.ignore_tags:
            self.recording = False
        else:
            self.recording = True

    def handle_endtag(self, tag):
        if tag.lower() in self.ignore_tags:
            self.recording = True

    def handle_data(self, data):
        if self.recording:
            cleaned = data.strip()
            if cleaned:
                self.text_chunks.append(cleaned)

    def get_text(self) -> str:
        return " ".join(self.text_chunks)


class WebScraper:
    @staticmethod
    def scrape_url(url: str, max_chars: int = 1500) -> str:
        """Fetches a web page and returns its cleaned text content."""
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                html_content = response.read().decode('utf-8', errors='ignore')
                
            parser = TextExtractParser()
            parser.feed(html_content)
            text = parser.get_text()
            
            # Clean whitespaces
            text = re.sub(r'\s+', ' ', text).strip()
            
            if len(text) > max_chars:
                return text[:max_chars] + "... [truncated]"
            return text
        except Exception as e:
            return f"Failed to scrape URL {url}: {e}"

    @staticmethod
    def search(query: str, num_results: int = 3) -> List[Dict[str, str]]:
        """Performs a search using DuckDuckGo HTML search and returns titles/snippets/urls."""
        encoded_query = urllib.parse.quote(query)
        # Using DuckDuckGo HTML-only search
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                html_content = response.read().decode('utf-8', errors='ignore')

            results = []
            # Find result snippets. In DuckDuckGo HTML, results are in class "result"
            # We can use simple regex to extract results, titles, snippets, and URLs to keep it dependency-free.
            result_blocks = re.findall(r'<div class="result results_links results_links_deep web-result ">([\s\S]*?)</div>\s*</div>\s*</div>', html_content)
            if not result_blocks:
                # Fallback to general result links matching
                result_blocks = re.findall(r'<a class="result__url"[\s\S]*?</a>', html_content)[:num_results]
                
            for block in result_blocks[:num_results]:
                title_match = re.search(r'<a class="result__snippet"[\s\S]*?>([\s\S]*?)</a>', block)
                url_match = re.search(r'href="([^"]+)"', block)
                snippet_match = re.search(r'<a class="result__snippet"[\s\S]*?>([\s\S]*?)</a>', block)
                
                # Broaden regex patterns
                title_m = re.search(r'<a class="result__a"[^>]*>([\s\S]*?)</a>', block)
                snippet_m = re.search(r'<a class="result__snippet"[^>]*>([\s\S]*?)</a>', block)
                
                title = re.sub(r'<[^>]+>', '', title_m.group(1)).strip() if title_m else "No Title"
                snippet = re.sub(r'<[^>]+>', '', snippet_m.group(1)).strip() if snippet_m else "No Snippet"
                res_url = urllib.parse.unquote(url_match.group(1)) if url_match else ""
                
                # Clean DuckDuckGo redirect URLs if present
                if res_url.startswith("//duckduckgo.com/l/?uddg="):
                    res_url = res_url.split("uddg=")[1].split("&")[0]
                elif "/l/?uddg=" in res_url:
                    res_url = res_url.split("/l/?uddg=")[1].split("&")[0]
                    res_url = urllib.parse.unquote(res_url)

                if title or snippet:
                    results.append({
                        "title": title,
                        "snippet": snippet,
                        "url": res_url
                    })
            return results
        except Exception:
            return []
