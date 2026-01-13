import pandas as pd
import os
import hashlib
from threading import Lock
from datetime import datetime
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class JobCache:
    def __init__(self, csv_path: str = 'data/jobs.csv', persist_interval: int = 50):
        self.csv_path = csv_path
        self.persist_interval = persist_interval
        self.changes_count = 0
        self.lock = Lock()
        
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        
        if os.path.exists(csv_path):
            logger.info(f"Loading existing jobs from {csv_path}")
            self.df = pd.read_csv(csv_path)
            logger.info(f"Loaded {len(self.df)} existing jobs")
        else:
            logger.info("Creating new jobs database")
            self.df = pd.DataFrame(columns=['title', 'company', 'location', 'url', 'snippet', 'posted_date', 'found_date', 'url_hash'])
        
        if 'url_hash' in self.df.columns and len(self.df) > 0:
            self.url_hashes = set(self.df['url_hash'].values)
        else:
            self.url_hashes = set()
            if 'url_hash' not in self.df.columns:
                self.df['url_hash'] = ''
        
        logger.info(f"JobCache initialized with {len(self.url_hashes)} unique URLs")
    
    def _hash_url(self, url: str) -> str:
        normalized = url.lower().strip().rstrip('/')
        if '?' in normalized:
            normalized = normalized.split('?')[0]
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def is_duplicate(self, url: str) -> bool:
        url_hash = self._hash_url(url)
        return url_hash in self.url_hashes
    
    def add_job(self, job_data: Dict) -> bool:
        url_hash = self._hash_url(job_data['url'])
        
        if url_hash in self.url_hashes:
            logger.debug(f"Duplicate job skipped: {job_data.get('title', 'Unknown')}")
            return False
        
        with self.lock:
            self.url_hashes.add(url_hash)
            job_data['url_hash'] = url_hash
            job_data['found_date'] = datetime.now().isoformat()
            
            for field in ['title', 'company', 'location', 'snippet', 'posted_date']:
                if field not in job_data:
                    job_data[field] = ''
            
            self.df = pd.concat([self.df, pd.DataFrame([job_data])], ignore_index=True)
            self.changes_count += 1
            logger.info(f"Added new job: {job_data.get('title', 'Unknown')}")
            
            if self.changes_count >= self.persist_interval:
                self.persist()
            
            return True
    
    def persist(self):
        with self.lock:
            self.df.to_csv(self.csv_path, index=False)
            self.changes_count = 0
            logger.info(f"Persisted {len(self.df)} jobs to {self.csv_path}")
    
    def get_stats(self) -> Dict:
        return {
            'total_jobs': len(self.df),
            'unique_urls': len(self.url_hashes),
            'changes_pending': self.changes_count,
            'csv_path': self.csv_path
        }