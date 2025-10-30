import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time

logger = logging.getLogger(__name__)

def scrape_linkedin_profile(linkedin_url, timeout=30000):
    """
    Scrape LinkedIn profile using Playwright to extract name, title, and company.
    
    Args:
        linkedin_url: The LinkedIn profile URL to scrape
        timeout: Timeout in milliseconds (default: 30000ms = 30s)
    
    Returns:
        dict with keys: name, title, company, location
        or None if scraping fails
    """
    try:
        with sync_playwright() as p:
            # Launch browser in headless mode
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            
            # Create context with realistic user agent
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = context.new_page()
            
            logger.info(f"Visiting LinkedIn profile: {linkedin_url}")
            
            # Navigate to the profile page
            response = page.goto(linkedin_url, wait_until='domcontentloaded', timeout=timeout)
            
            if not response or response.status != 200:
                logger.error(f"Failed to load page, status: {response.status if response else 'None'}")
                browser.close()
                return None
            
            # Wait a bit for dynamic content
            time.sleep(2)
            
            # Extract profile information
            profile_data = {}
            
            # Extract name (h1 tag)
            try:
                name_element = page.query_selector('h1.text-heading-xlarge, h1')
                if name_element:
                    profile_data['name'] = name_element.inner_text().strip()
                else:
                    profile_data['name'] = 'Not Found'
            except Exception as e:
                logger.warning(f"Could not extract name: {str(e)}")
                profile_data['name'] = 'Not Found'
            
            # Extract title/headline (div with class containing 'headline')
            try:
                title_element = page.query_selector('div.text-body-medium, div[class*="headline"], .pv-text-details__left-panel h2')
                if title_element:
                    profile_data['title'] = title_element.inner_text().strip()
                else:
                    profile_data['title'] = 'Not Found'
            except Exception as e:
                logger.warning(f"Could not extract title: {str(e)}")
                profile_data['title'] = 'Not Found'
            
            # Extract company
            try:
                company_element = page.query_selector('div.inline-show-more-text, div[class*="company"]')
                if company_element:
                    profile_data['company'] = company_element.inner_text().strip()
                else:
                    profile_data['company'] = 'Not Found'
            except Exception as e:
                logger.warning(f"Could not extract company: {str(e)}")
                profile_data['company'] = 'Not Found'
            
            # Extract location
            try:
                location_element = page.query_selector('span.text-body-small, div[class*="location"]')
                if location_element:
                    profile_data['location'] = location_element.inner_text().strip()
                else:
                    profile_data['location'] = 'Not Found'
            except Exception as e:
                logger.warning(f"Could not extract location: {str(e)}")
                profile_data['location'] = 'Not Found'
            
            browser.close()
            
            logger.info(f"Successfully scraped profile: {profile_data.get('name', 'Unknown')}")
            return profile_data
            
    except PlaywrightTimeoutError:
        logger.error(f"Timeout while loading LinkedIn profile: {linkedin_url}")
        return None
    except Exception as e:
        logger.error(f"Error scraping LinkedIn profile: {str(e)}")
        return None
