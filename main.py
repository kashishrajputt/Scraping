import asyncio
import logging
from typing import List, Dict, Any
from playwright.async_api import async_playwright

from config import BASE_URL, HEADLESS, MAX_RESULTS
from logger import logger
from scapper import (
    open_case_status_page,
    enumerate_high_courts,
    enumerate_benches,
    perform_search_and_extract
)
from utils import parse_date
from database import init_database, insert_case_record


class ECourtsScraper:
    """Main scraper class for eCourts High Court Case Status portal"""
    
    def __init__(self, headless: bool = HEADLESS):
        self.headless = headless
        self.browser = None
        self.page = None
        
    async def __aenter__(self):
       
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        self.page = await self.browser.new_page()
        
        
        await self.page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        
        if self.browser:
            await self.browser.close()
    
    async def initialize(self) -> bool:
        
        try:
            logger.info(f" Initializing scraper - navigating to {BASE_URL}")
            await self.page.goto(BASE_URL, wait_until='networkidle')
            await self.page.wait_for_timeout(2000)
            
            # Open Case Status section
            success = await open_case_status_page(self.page)
            if not success:
                logger.error(" Failed to open Case Status section")
                return False
                
            logger.info(" Successfully initialized scraper")
            return True
            
        except Exception as e:
            logger.error(f" Failed to initialize scraper: {e}")
            return False
    
    async def get_all_high_courts(self) -> List[Dict[str, str]]:
        
        try:
            logger.info(" Enumerating all High Courts...")
            courts = await enumerate_high_courts(self.page)
            logger.info(f" Found {len(courts)} High Courts")
            
            # Log all courts for reference
            for court in courts:
                logger.info(f"  - {court['text']} (value: {court['value']})")
                
            return courts
            
        except Exception as e:
            logger.error(f" Failed to enumerate High Courts: {e}")
            return []
    
    async def get_benches_for_court(self, court_value: str, court_name: str) -> List[Dict[str, str]]:
        
        try:
            logger.info(f" Enumerating benches for {court_name}...")
            benches = await enumerate_benches(self.page, court_value)
            logger.info(f" Found {len(benches)} benches for {court_name}")
        
            
            # Log all benches for reference
            for bench in benches:
                logger.info(f"  - {bench['text']} (value: {bench['value']})")
                
            return benches
            
        except Exception as e:
            logger.error(f" Failed to enumerate benches for {court_name}: {e}")
            return []
    
    async def search_by_party_name(self, court_name: str, court_value: str, bench_value: str, bench_name: str, 
                                 party_name: str) -> List[Dict[str, Any]]:
        
        logger.info(f" Searching by party name: '{party_name}' in {court_name} - {bench_name}")
        results = await perform_search_and_extract(
            self.page, court_name, court_value, bench_value, bench_name, "party_name", party_name
        )
        logger.info(f" Found {len(results)} results for party name search")
        return results
    
    
    
    async def perform_search(self, court_name: str, court_value: str, bench_name: str, bench_value: str, party_name: str) -> List[Dict[str, Any]]:
       
        results = await self.search_by_party_name(court_name, court_value, bench_value, bench_name, party_name)
        return results
    
    async def save_to_database(self, case_results: List[Dict[str, Any]]) -> bool:
        
        try:
            for record in case_results:
                insert_case_record(record)
            return True
        except Exception as e:
            logger.error(f"Failed to save to database: {e}")
            return False
    
    async def run_comprehensive_search(self):
        logger.info("Starting comprehensive search...")

        
        courts = await self.get_all_high_courts()
        logger.info(f"Total courts found: {len(courts)}")

        
        target_court_values = ['26', '3']  
        filtered_courts = [c for c in courts if c['value'] in target_court_values]

        if not filtered_courts:
            logger.error("No matching courts found for Delhi/Karnataka! Check dropdown names or values.")
            logger.info(f"Available courts: {[c['text'] for c in courts]}")
            return

        logger.info(f"Courts to process: {[c['text'] for c in filtered_courts]}")

        total_processed = 0
        total_cases = 0

        for court in filtered_courts:
            court_name = court['text']
            court_value = court['value']

            logger.info(f" Processing court: {court_name} (value: {court_value})")

            
            benches = await self.get_benches_for_court(court_value, court_name)
            logger.info(f"Benches found: {len(benches)} for {court_name}")

            if not benches:
                logger.warning(f" No benches found for {court_name}, skipping...")
                continue

            for bench in benches:
                bench_name = bench['text']
                bench_value = bench['value']
                logger.info(f"    Searching in bench: {bench_name}")

                search_party_name = "kumar"  # Change to something that yields results
                search_case_number = "123"  # Placeholder if needed

                try:
                    case_results = await self.perform_search(
                        court_name=court_name,
                        court_value=court_value,
                        bench_name=bench_name,
                        bench_value=bench_value,
                        party_name=search_party_name
                    )

                    if case_results:
                        total_cases += len(case_results)
                        await self.save_to_database(case_results)
                        logger.info(f" {len(case_results)} cases saved for {bench_name}")
                    else:
                        logger.info(f" No results found for {bench_name}")

                except Exception as e:
                    logger.error(f"Error during search in {bench_name}: {e}")

            total_processed += 1

        logger.info(f"Courts processed: {total_processed}")
        logger.info(f"Total case results collected: {total_cases}")


async def main():
    """Main entry point"""
    logger.info(" Starting eCourts High Court Case Status Scraper")
    
    
    try:
        init_database()
        logger.info(" Database initialized")
    except Exception as e:
        logger.warning(f" Database initialization failed: {e}")
    
   
    async with ECourtsScraper(headless=False) as scraper:
     
        if not await scraper.initialize():
            logger.error(" Failed to initialize scraper")
            return
        
      
        results = await scraper.run_comprehensive_search()
        
     
        logger.info(" SEARCH SUMMARY:")
        logger.info(f"  - High Courts found: {len(results['high_courts'])}")
        logger.info(f"  - Courts processed: {len(results['searches'])}")
        logger.info(f"  - Total case results: {results['total_results']}")
        
        for search in results['searches']:
            logger.info(f"  - {search['court_name']} ({search['bench_name']}):")
            for party_search in search['party_name_searches']:
                logger.info(f"    * Party '{party_search['query']}': {party_search['count']} results")
            for case_search in search['case_number_searches']:
                logger.info(f"    * Case '{case_search['query']}': {case_search['count']} results")


if __name__ == "__main__":
    asyncio.run(main())
