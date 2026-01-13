from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class GoogleSearchClient:
    def __init__(self, api_key: str, search_engine_id: str):
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.service = None
        self.request_count = 0
        logger.info("GoogleSearchClient initialized")
    
    def _get_service(self):
        if self.service is None:
            self.service = build("customsearch", "v1", developerKey=self.api_key)
        return self.service
    
    def search(self, query: str, location: str = "", num_results: int = 10, max_retries: int = 3) -> List[Dict]:
        full_query = f"{query} {location}".strip()
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Searching: {full_query} (attempt {attempt + 1}/{max_retries})")
                service = self._get_service()
                result = service.cse().list(q=full_query, cx=self.search_engine_id, num=min(num_results, 10)).execute()
                
                self.request_count += 1
                items = result.get('items', [])
                
                parsed_results = []
                for item in items:
                    parsed_results.append({
                        'title': item.get('title', ''),
                        'url': item.get('link', ''),
                        'snippet': item.get('snippet', ''),
                        'displayLink': item.get('displayLink', ''),
                        'formattedUrl': item.get('formattedUrl', '')
                    })
                
                logger.info(f"✓ Found {len(parsed_results)} results for: {full_query}")
                return parsed_results
                
            except HttpError as e:
                if e.resp.status == 429:
                    wait_time = 2 ** attempt
                    logger.warning(f"Rate limited. Waiting {wait_time}s...")
                    time.sleep(wait_time)
                elif e.resp.status == 403:
                    logger.error("API quota exceeded!")
                    raise
                else:
                    logger.error(f"HTTP error: {e}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Search error: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
        
        logger.warning(f"Search failed after {max_retries} attempts: {full_query}")
        return []
    
    def get_stats(self) -> Dict:
        return {'total_requests': self.request_count, 'api_key': f"{self.api_key[:10]}..." if self.api_key else None, 'search_engine_id': self.search_engine_id}
        