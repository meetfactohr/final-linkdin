import logging
import os
import json
import requests
from typing import Optional
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time

logger = logging.getLogger(__name__)

def _classify_title_gemini(title: str, role: str, api_key: str) -> Optional[bool]:
    """
    Use the Google Gemini API to determine whether a LinkedIn title matches the
    requested role.

    The function returns True if the title appears to describe the requested
    role, False if it clearly does not, and None if the classification could
    not be performed (e.g. due to missing API key or errors).

    Only ambiguous titles should be passed to this function.  Titles that
    already contain the role keyword should be treated as matches without
    calling this API.

    Args:
        title: The LinkedIn headline/title extracted from the profile.
        role: The role being searched (e.g. "hr", "ceo").
        api_key: A valid Gemini API key.  If empty, classification is skipped.

    Returns:
        True if the title matches the role, False if it does not, or None on
        failure.
    """
    if not api_key:
        return None
    # Construct a prompt asking whether the title corresponds to the given role.
    prompt = (
        "You are an expert role classifier. Consider the job title below and "
        "determine if it clearly represents someone working as '{role}'. "
        "Respond with 'yes' if the person appears to be a {role}, or 'no' if "
        "they are not. Only answer 'yes' or 'no'.\n\n"
        f"Title: {title}\n"
        f"Role: {role}\n"
    ).format(role=role)
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent"
        f"?key={api_key}"
    )
    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code != 200:
            return None
        result = response.json()
        # Extract the first candidate's response text
        text = None
        if isinstance(result, dict):
            candidates = result.get("candidates")
            if candidates and isinstance(candidates, list):
                first = candidates[0]
                content = first.get("content") if isinstance(first, dict) else None
                if content and isinstance(content, dict):
                    parts = content.get("parts")
                    if parts and isinstance(parts, list):
                        first_part = parts[0]
                        if isinstance(first_part, dict):
                            text = first_part.get("text")
        if text:
            text = text.strip().lower()
            if 'yes' in text:
                return True
            if 'no' in text:
                return False
        return None
    except Exception:
        # Do not raise errors; return None to indicate failure
        return None

def scrape_linkedin_profile(linkedin_url: str, role: Optional[str] = None, timeout: int = 30000) -> Optional[dict]:
    """
    Scrape a LinkedIn profile using Playwright to extract name, title, company
    and location.  Optionally classify whether the title matches a specific
    role using the Gemini API.

    Args:
        linkedin_url: The LinkedIn profile URL to scrape.
        role: Optional role to classify (e.g. "hr", "ceo").  If provided,
            the function will attempt to determine whether the scraped title
            matches this role.  Matching is determined by keyword heuristics
            and, when necessary, by querying the Gemini API.  Classification
            results are returned in the ``role_match`` field of the profile
            dictionary.  If no role is provided, classification is skipped.
        timeout: Timeout in milliseconds (default: 30000ms = 30s).

    Returns:
        A dictionary with keys: ``name``, ``title``, ``company``, ``location`` and
        optionally ``role_match`` if ``role`` was supplied.  Returns ``None`` on
        scraping failure.
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

            # If LinkedIn returns a non‑200 status (e.g. 999 for blocked requests), attempt a
            # single retry after a short pause.  LinkedIn sometimes returns status 999 when
            # access is blocked; waiting and reloading may succeed if a proxy is used.
            if not response or response.status != 200:
                status_code = response.status if response else 'None'
                logger.warning(f"Initial page load returned status {status_code} for {linkedin_url}")
                if status_code == 999:
                    # Wait briefly and retry once
                    time.sleep(5)
                    response_retry = page.goto(linkedin_url, wait_until='domcontentloaded', timeout=timeout)
                    if response_retry and response_retry.status == 200:
                        response = response_retry
                    else:
                        logger.error(f"Failed to load page after retry, status: {response_retry.status if response_retry else 'None'}")
                        browser.close()
                        return None
                else:
                    browser.close()
                    return None
            
            # Wait a bit for dynamic content
            time.sleep(2)
            
            # Extract profile information
            profile_data: dict = {}
            
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

            # Perform role classification if a role is provided and a title was found
            if role:
                role_lower = role.strip().lower() if isinstance(role, str) else ''
                title_text = profile_data.get('title', '') or ''
                # By default, assume match if the role keyword appears in the title
                match: Optional[bool] = None
                if role_lower and role_lower in title_text.lower():
                    match = True
                else:
                    # Use Gemini for ambiguous titles; only call if API key is configured
                    api_key = os.environ.get('GAIMINI_API_KEY', '')
                    match = _classify_title_gemini(title_text, role_lower, api_key)
                profile_data['role_match'] = match

            logger.info(f"Successfully scraped profile: {profile_data.get('name', 'Unknown')}")
            return profile_data
            
    except PlaywrightTimeoutError:
        logger.error(f"Timeout while loading LinkedIn profile: {linkedin_url}")
        return None
    except Exception as e:
        logger.error(f"Error scraping LinkedIn profile: {str(e)}")
        return None
