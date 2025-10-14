import logging
import asyncio
import requests
from playwright.async_api import async_playwright, Page
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

from logger import logger
from utils import parse_date
from database import insert_case_record, log_search
from captcha_solver import solve_captcha

async def open_case_status_page(page):
    selectors = [
        "text=Case Status",
        "a:has-text('Case Status')",
        "#case_status_link",
    ]
    for sel in selectors:
        try:
            await page.locator(sel).first.click(timeout=2000)
            logger.info("✅ Clicked Case Status link using %s", sel)
            await page.wait_for_load_state("networkidle")
            
            # Handle popup if it appears
            await handle_popup_if_present(page)
            
            return True
        except Exception:
            continue

    logger.info("Proceeding with loaded page (could not click explicit Case Status link)")
    # Still try to handle popup even if we couldn't click the link
    await handle_popup_if_present(page)
    return True


async def handle_popup_if_present(page):
    
    try:
        
        await page.wait_for_timeout(1000)
        
        
        popup_selectors = [
            "button:has-text('OK')",
            "button:has-text('Okay')", 
            "button:has-text('Close')",
            "input[value='OK']",
            "input[value='Okay']",
            "input[value='Close']",
            ".popup button",
            ".modal button",
            "#popup button",
            "button[onclick*='close']",
            "button[onclick*='hide']"
        ]
        
        for selector in popup_selectors:
            try:
                popup_button = page.locator(selector).first
                if await popup_button.is_visible(timeout=1000):
                    await popup_button.click()
                    logger.info("Dismissed popup using selector: %s", selector)
                    await page.wait_for_timeout(500)
                    return True
            except Exception:
                continue
                
        
        try:
            await page.keyboard.press("Escape")
            logger.info(" Pressed Escape to dismiss popup")
            await page.wait_for_timeout(500)
        except Exception:
            pass
            
        logger.debug("No popup detected or already dismissed")
        
    except Exception as e:
        logger.debug(f"Popup handling error (non-critical): {e}")


async def enumerate_high_courts(page):
    """Enumerate available High Courts using the correct selector."""
    try:
        
        select = page.locator("#sess_state_code")
        if not await select.is_visible():
            logger.warning(" High Court dropdown not visible")
            return []
            
        options = await select.locator("option").all()
        courts = []
        
        for opt in options:
            val = await opt.get_attribute("value")
            text = await opt.inner_text()
            if val and val.strip() and val != "0":  
                courts.append({"value": val.strip(), "text": text.strip()})

        logger.info("Enumerated %d high courts", len(courts))
        return courts
        
    except Exception as e:
        logger.error(f" Failed to enumerate high courts: {e}")
        return []


async def enumerate_benches(page, court_value: str):
    """
    Robust bench enumerator for any High Court.
    Returns a list of dicts: {"value": ..., "text": ...}
    """
    benches = []

    
    await page.select_option("#sess_state_code", court_value)
    print(f"Selected High Court value: {court_value}")

    
    bench_frame = None

    
    for attempt in range(10):
        for f in page.frames:
            try:
                if await f.query_selector("#court_complex_code"):
                    bench_frame = f
                    break
            except:
                continue
        if bench_frame:
            break
        await asyncio.sleep(1)

    target = bench_frame or page

    
    try:
        await target.wait_for_function(
            """() => {
                const el = document.querySelector('#court_complex_code');
                return el && el.options.length > 1;
            }""",
            timeout=20000
        )
    except Exception:
        print(" Timeout waiting for bench dropdown to populate")
        return benches

    
    try:
        options = await target.eval_on_selector_all(
            "#court_complex_code option",
            "opts => opts.map(o => ({ text: o.textContent.trim(), value: o.value }))"
        )
        benches = [o for o in options if o['value'].strip() and 'Select' not in o['text']]
        print(f" Found {len(benches)} benches for court value {court_value}")
    except Exception as e:
        print(f"Failed to extract benches: {e}")

    return benches


async def perform_search_and_extract(
    page: Page,
    court_code: str,
    state_code: str,
    court_complex_code: str,
    search_type: str,
    query: str,
    year: str = "2024",
    max_retries: int = 3
) -> List[Dict[str, Any]]:
    """
    Perform search on eCourts via direct POST request using session cookies from Playwright.
    """
    post_url = "https://hcservices.ecourts.gov.in/hcservices/cases_qry/index_qry.php"
    captcha_url = "https://hcservices.ecourts.gov.in/hcservices/securimage/securimage_show.php?14"

   
    cookies = await page.context.cookies()
    session_cookies = {cookie['name']: cookie['value'] for cookie in cookies}

    
    try:
        session = requests.Session()
        session.cookies.update(session_cookies)
        response = session.get(captcha_url, timeout=10)
        response.raise_for_status()
        captcha_image_bytes = response.content

       
        captcha_solution = solve_captcha(captcha_image_bytes)
    except Exception as e:
        logger.error(f"Failed to solve CAPTCHA: {e}")
        return []
    if not captcha_solution:
        logger.error("Failed to solve CAPTCHA")
        return []

    logger.info(f"CAPTCHA solved: {captcha_solution}")

    
    payload = {
        "court_code": court_code,
        "state_code": state_code,
        "court_complex_code": court_complex_code,
        "caseStatusSearchType": "CSpartyName" if search_type == "party_name" else "CScaseNumber",
        "captcha": captcha_solution,
        "f": "Both",  # seems fixed
        "petres_name": query if search_type == "party_name" else "",
        "caseNo": query if search_type == "case_number" else "",
        "rgyear": year
    }

   
    for attempt in range(max_retries):
        try:
            logger.info(f"POST attempt {attempt + 1}/{max_retries}")
            response = session.post(post_url, data=payload, timeout=15)
            response.raise_for_status()

            
            soup = BeautifulSoup(response.text, "html.parser")
            results_table = soup.select_one("table#searchResults")  
            if not results_table:
                results_table = soup.find("table", id="dispTable")

                await asyncio.sleep(2)
                continue

            results = []
            rows = results_table.select("tr")[1:]  
            for row in rows:
                cols = row.select("td")
                results.append({
                    "case_number": cols[0].get_text(strip=True),
                    "party_name": cols[1].get_text(strip=True),
                    "next_date": cols[2].get_text(strip=True),
                    "status": cols[3].get_text(strip=True),
                  
                })

            logger.info(f"Found {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Error on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
                continue
            return []
    return []
