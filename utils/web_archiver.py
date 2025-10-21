"""Web page archiving utilities for link management."""

import httpx
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
import logging
import re
from urllib.parse import urlparse, urljoin
import html2text
from datetime import datetime

logger = logging.getLogger(__name__)


class WebArchiver:
    """Archive web pages with content extraction and metadata."""

    def __init__(self):
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False
        self.html_converter.body_width = 0  # Don't wrap text

    async def archive_url(self, url: str) -> Dict[str, Any]:
        """
        Archive a web page completely.

        Args:
            url: The URL to archive

        Returns:
            Dictionary containing:
                - title: Page title
                - content: Main content as markdown
                - html: Original HTML
                - metadata: Meta tags and info
                - text: Plain text content
                - success: Whether archival succeeded
                - error: Error message if failed
        """
        try:
            # Validate URL
            if not self._is_valid_url(url):
                return {
                    'success': False,
                    'error': 'Invalid URL format',
                    'url': url
                }

            # Fetch the page
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                response = await client.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response.raise_for_status()

            html_content = response.text
            final_url = str(response.url)  # After redirects

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            # Extract metadata
            metadata = self._extract_metadata(soup, final_url)

            # Extract main content
            main_content = self._extract_main_content(soup)

            # Convert to markdown
            markdown_content = self.html_converter.handle(str(main_content))

            # Extract plain text
            text_content = main_content.get_text(separator='\n', strip=True)

            # Get word count
            word_count = len(text_content.split())

            return {
                'success': True,
                'url': final_url,
                'original_url': url,
                'title': metadata['title'],
                'description': metadata['description'],
                'author': metadata.get('author'),
                'site_name': metadata.get('site_name'),
                'favicon': metadata.get('favicon'),
                'published_date': metadata.get('published_date'),
                'content_markdown': markdown_content,
                'content_text': text_content,
                'content_html': str(main_content),
                'full_html': html_content,
                'word_count': word_count,
                'metadata': metadata,
                'archived_at': datetime.utcnow().isoformat(),
                'error': None
            }

        except httpx.HTTPError as e:
            logger.error(f"HTTP error archiving {url}: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to fetch page: {str(e)}',
                'url': url
            }
        except Exception as e:
            logger.error(f"Error archiving {url}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'url': url
            }

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme in ['http', 'https'], result.netloc])
        except Exception:
            return False

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract metadata from HTML."""
        metadata = {}

        # Title
        title_tag = soup.find('title')
        og_title = soup.find('meta', property='og:title')
        twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})

        metadata['title'] = (
            og_title['content'] if og_title else
            twitter_title['content'] if twitter_title else
            title_tag.string if title_tag else
            'Untitled'
        )

        # Description
        description_tag = soup.find('meta', attrs={'name': 'description'})
        og_description = soup.find('meta', property='og:description')
        twitter_description = soup.find('meta', attrs={'name': 'twitter:description'})

        metadata['description'] = (
            og_description['content'] if og_description else
            twitter_description['content'] if twitter_description else
            description_tag['content'] if description_tag else
            ''
        )

        # Author
        author_tag = soup.find('meta', attrs={'name': 'author'})
        metadata['author'] = author_tag['content'] if author_tag else None

        # Site name
        site_name = soup.find('meta', property='og:site_name')
        metadata['site_name'] = site_name['content'] if site_name else urlparse(url).netloc

        # Favicon
        favicon = soup.find('link', rel='icon') or soup.find('link', rel='shortcut icon')
        if favicon and favicon.get('href'):
            favicon_url = urljoin(url, favicon['href'])
            metadata['favicon'] = favicon_url
        else:
            # Default favicon location
            parsed_url = urlparse(url)
            metadata['favicon'] = f"{parsed_url.scheme}://{parsed_url.netloc}/favicon.ico"

        # Published date
        published = (
            soup.find('meta', property='article:published_time') or
            soup.find('meta', attrs={'name': 'publish_date'}) or
            soup.find('time', attrs={'datetime': True})
        )

        if published:
            if hasattr(published, 'get'):
                metadata['published_date'] = published.get('content') or published.get('datetime')
            elif hasattr(published, 'attrs'):
                metadata['published_date'] = published.attrs.get('datetime')
        else:
            metadata['published_date'] = None

        # Image
        og_image = soup.find('meta', property='og:image')
        twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
        metadata['image'] = (
            og_image['content'] if og_image else
            twitter_image['content'] if twitter_image else
            None
        )

        # Keywords
        keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
        if keywords_tag:
            keywords = [k.strip() for k in keywords_tag['content'].split(',')]
            metadata['keywords'] = keywords
        else:
            metadata['keywords'] = []

        return metadata

    def _extract_main_content(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Extract the main content from the page, removing nav, ads, etc."""
        # Remove unwanted elements
        for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()

        # Remove ads and tracking
        for element in soup.find_all(class_=re.compile('ad|advertisement|banner|sidebar|promo', re.I)):
            element.decompose()

        # Try to find main content
        main_content = (
            soup.find('article') or
            soup.find('main') or
            soup.find('div', class_=re.compile('content|article|post|entry', re.I)) or
            soup.find('body')
        )

        return main_content if main_content else soup

    async def extract_links_from_page(self, url: str) -> Dict[str, Any]:
        """Extract all links from a web page."""
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
                response = await client.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            links = []

            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(url, href)

                # Only include http/https links
                if absolute_url.startswith(('http://', 'https://')):
                    links.append({
                        'url': absolute_url,
                        'text': link.get_text(strip=True),
                        'title': link.get('title', '')
                    })

            return {
                'success': True,
                'url': url,
                'links': links,
                'count': len(links)
            }

        except Exception as e:
            logger.error(f"Error extracting links from {url}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'url': url
            }

    def generate_summary(self, text: str, max_length: int = 500) -> str:
        """Generate a simple extractive summary."""
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)

        # Clean and filter sentences
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

        # Take first few sentences until we hit max_length
        summary = ""
        for sentence in sentences[:5]:  # Max 5 sentences
            if len(summary) + len(sentence) > max_length:
                break
            summary += sentence + ". "

        return summary.strip() or text[:max_length]

    async def get_page_metadata_only(self, url: str) -> Dict[str, Any]:
        """
        Quickly fetch just the metadata without full archival.
        Useful for link previews.
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
                response = await client.get(url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            metadata = self._extract_metadata(soup, str(response.url))

            return {
                'success': True,
                'url': str(response.url),
                'title': metadata['title'],
                'description': metadata['description'],
                'favicon': metadata.get('favicon'),
                'image': metadata.get('image'),
                'site_name': metadata.get('site_name')
            }

        except Exception as e:
            logger.error(f"Error fetching metadata for {url}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'url': url
            }
