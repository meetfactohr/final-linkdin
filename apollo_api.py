import logging
import requests
import os

logger = logging.getLogger(__name__)

APOLLO_API_KEY = os.environ.get('APOLLO_API_KEY', '')

def find_email_apollo(domain, name=None, title=None):
    """
    Find email using Apollo API.
    
    Args:
        domain: Company domain
        name: Person's full name (optional)
        title: Person's job title (optional)
    
    Returns:
        Email address string or None if not found
    """
    try:
        if not APOLLO_API_KEY:
            logger.error("Apollo API key not configured")
            return None
        
        url = "https://api.apollo.io/v1/mixed_people/search"
        
        # Build search payload
        payload = {
            "api_key": APOLLO_API_KEY,
            "q_organization_domains": [domain],
            "page": 1,
            "per_page": 10
        }
        
        # Add optional filters
        if title:
            payload["person_titles"] = [title]
        
        if name:
            payload["q_keywords"] = name
        
        logger.info(f"Searching Apollo for email at {domain}" + 
                   (f" with title: {title}" if title else "") +
                   (f" and name: {name}" if name else ""))
        
        response = requests.post(url, json=payload, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'people' in data and len(data['people']) > 0:
                for person in data['people']:
                    email = person.get('email')
                    
                    # Validate email exists and is not a placeholder
                    if email and '@' in email and not email.endswith('@example.com'):
                        person_name = person.get('name', '')
                        person_title = person.get('title', '')
                        
                        logger.info(f"Found email via Apollo: {email} ({person_name} - {person_title})")
                        return email
                
                logger.info(f"No valid email found in Apollo results for {domain}")
                return None
            else:
                logger.info(f"No people found in Apollo for {domain}")
                return None
        
        elif response.status_code == 429:
            logger.warning("Apollo API rate limit reached")
            return None
        elif response.status_code == 401:
            logger.error("Apollo API authentication failed - check API key")
            return None
        else:
            logger.warning(f"Apollo API returned status {response.status_code}: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        logger.error("Apollo API request timed out")
        return None
    except Exception as e:
        logger.error(f"Error finding email with Apollo: {str(e)}")
        return None
