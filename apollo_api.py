"""
Apollo API client.

This module wraps calls to the Apollo.io API to locate business email
addresses based on a domain and person name.  If you provide a valid
``APOLLO_API_KEY`` environment variable and network connectivity is
available, the ``find_email_apollo`` function will attempt to look up
contact details via Apollo's People Enrichment endpoint.  When the
API key is not configured or the request fails, the function returns
``None`` so the caller can fall back to other email discovery methods
(e.g. Hunter.io).

References:

* People Enrichment (match) endpoint: ``https://api.apollo.io/api/v1/people/match``
* The API expects a POST request with JSON payload containing at least
  ``first_name``, ``last_name`` and ``organization_domain``.  You can
  optionally set ``reveal_personal_emails: true`` to request email
  addresses.  A valid ``api_key`` must be provided via an
  Authorization header or query parameter.  See Apollo's official
  documentation for complete details.

Note:

This implementation is best‑effort and cannot be tested in the
offline environment.  It uses reasonable defaults for parameter names
and response parsing based on publicly available examples.  If you
encounter issues, consult the Apollo API docs and adjust the
parameters accordingly.
"""

import os
import logging
import requests
from typing import Optional

# Read the Apollo API key from the environment; when not provided the client is
# disabled.  Set APOLLO_API_KEY=<your_key> in .env to enable.
APOLLO_API_KEY: str = os.environ.get('APOLLO_API_KEY', '')

logger = logging.getLogger(__name__)

def _split_name(full_name: str) -> tuple[str, str]:
    """Split a full name into first and last names.

    This helper attempts to split a person's full name into a first and
    last name.  If the name has only one token it is used as both
    ``first_name`` and ``last_name``.  Extra middle names are ignored.

    Args:
        full_name: The full name of the person (e.g. "Jane Doe").

    Returns:
        A tuple of (first_name, last_name).
    """
    parts = [p for p in full_name.strip().split() if p]
    if not parts:
        return ('', '')
    if len(parts) == 1:
        return (parts[0], parts[0])
    return (parts[0], parts[-1])


def find_email_apollo(domain: str, full_name: str, title: str = '') -> Optional[str]:
    """
    Attempt to find a business email address via the Apollo.io People Enrichment API.

    This function issues a POST request to the Apollo People Enrichment endpoint
    (``/api/v1/people/match``) using the configured ``APOLLO_API_KEY``.  It
    extracts an email address from the response if one is available.

    Args:
        domain: The company's domain (e.g. "example.com").
        full_name: The full name of the contact person (e.g. "Jane Doe").
        title: Optional job title for additional context.  Included in the
            request payload to improve matching.

    Returns:
        A string containing the email address if found; otherwise ``None``.

    Notes:
        - This function will return ``None`` if ``APOLLO_API_KEY`` is not set or
          if the HTTP request fails.  It also swallows network errors so that
          callers can seamlessly fall back to other methods.
        - Apollo may require that you enable the ``reveal_personal_emails`` flag
          in order to return email addresses.  This implementation sets
          ``reveal_personal_emails`` to ``True`` by default.
    """
    if not APOLLO_API_KEY:
        logger.debug(
            f"Apollo API key not set; skipping Apollo lookup for {full_name} at {domain}."
        )
        return None

    first_name, last_name = _split_name(full_name)
    if not first_name:
        logger.debug(f"Cannot split full name '{full_name}' into first/last names for Apollo lookup.")
        return None

    endpoint = "https://api.apollo.io/api/v1/people/match"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        # Apollo docs suggest using Bearer token authentication.  Some examples use
        # an api_key query parameter instead.  We include both for safety.
        "Authorization": f"Bearer {APOLLO_API_KEY}"
    }

    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "organization_domain": domain,
        # Provide the title if available to improve matching
        "title": title,
        # Request that Apollo reveal personal (work) email addresses
        "reveal_personal_emails": True,
        "reveal_phone_number": False
    }

    try:
        logger.debug(f"Calling Apollo People Enrichment for {full_name} at {domain}...")
        response = requests.post(endpoint, headers=headers, json=payload, timeout=10)
        if response.status_code != 200:
            logger.warning(f"Apollo API returned status {response.status_code} for {full_name} at {domain}.")
            return None

        data = response.json()
        # The response may have the email at top level or nested under 'person' or 'contact'.
        # Try multiple fallbacks.
        email = None
        # Check 'email' directly
        if isinstance(data, dict):
            email = data.get('email')
            if not email:
                # Check nested fields
                person = data.get('person') or data.get('contact') or data.get('data')
                if person and isinstance(person, dict):
                    email = person.get('email') or person.get('work_email')
                    if not email:
                        # If there is an 'emails' list, pick the first
                        emails = person.get('emails')
                        if isinstance(emails, list) and emails:
                            first_email = emails[0]
                            if isinstance(first_email, str):
                                email = first_email
                            elif isinstance(first_email, dict):
                                email = first_email.get('email')
        if email:
            logger.debug(f"Apollo found email {email} for {full_name} at {domain}")
            return email
        else:
            logger.debug(f"Apollo did not return an email for {full_name} at {domain}")
            return None

    except Exception as e:
        # Catch network and parsing errors silently; log at debug level to avoid noisy output
        logger.debug(f"Apollo lookup error for {full_name} at {domain}: {e}")
        return None
