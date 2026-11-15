"""Session management for authenticated HTTP requests to inpol.mazowieckie.pl.

This module provides the SessionManager class for handling JWT-based
authentication with Bearer tokens.

Uses curl-cffi for TLS fingerprint impersonation to bypass Akamai bot protection.
"""

import logging
import re
import time
from typing import Optional

from curl_cffi.requests import Session
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages authenticated HTTP sessions with JWT Bearer tokens.

    Encapsulates curl_cffi.Session with JWT token management,
    automatic Authorization headers, and proper connection cleanup.

    Attributes:
        base_url: Base URL for the target site (e.g., https://inpol.mazowieckie.pl)
        session: Persistent curl_cffi.Session with cookies and headers
        jwt_token: JWT access token string
        logged_in: Boolean flag indicating valid authenticated session
    """

    def __init__(self, base_url: str, jwt_token: Optional[str] = None):
        """Initialize SessionManager with base URL and optional JWT token.

        Args:
            base_url: Base URL for the target site (e.g., https://inpol.mazowieckie.pl)
            jwt_token: Optional JWT access token for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.session = Session(impersonate='chrome124')
        self.jwt_token = jwt_token
        self.logged_in = False

        # Set browser headers to match Chrome 124 fingerprint
        # curl-cffi handles TLS fingerprint (JA3/JA3S) automatically
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9,pl;q=0.8',
            'Cache-Control': 'max-age=0',
            'Pragma': 'no-cache',
        })

        # Add Bearer token if provided
        if self.jwt_token:
            self.session.headers['Authorization'] = f'Bearer {self.jwt_token}'
            self.logged_in = True

        logger.debug(f"SessionManager initialized for {self.base_url} with chrome124 impersonation")

    def login(self, email: str, password: str) -> bool:
        """Authenticate using JWT-based login.

        Posts credentials to the /identity/sign-in endpoint and stores
        the returned JWT access token for subsequent API requests.

        Args:
            email: Account email address
            password: Account password

        Returns:
            True if login successful and access token received, False otherwise

        Notes:
            - Sets self.logged_in = True on success
            - Stores JWT token and adds Authorization: Bearer header
            - Uses JSON payload, not form data
        """
        login_url = f"{self.base_url}/identity/sign-in"

        logger.info(f"Authenticating to {login_url}")

        payload = {
            "email": email,
            "password": password
        }

        try:
            response = self.session.post(
                login_url,
                json=payload,
                timeout=30
            )

            logger.debug(f"Login response status: {response.status_code}")

            if response.status_code != 200:
                logger.error(f"Login failed: HTTP {response.status_code}")
                return False

            # Parse response JSON
            try:
                data = response.json()
            except Exception as e:
                logger.error(f"Failed to parse login response JSON: {e}")
                return False

            # Extract access token
            access_token = data.get('token')
            if not access_token:
                logger.error(f"Login response missing token: {data}")
                return False

            # Store token and set Authorization header
            self.jwt_token = access_token
            self.session.headers['Authorization'] = f'Bearer {access_token}'
            self.logged_in = True

            logger.info("Login successful - JWT token obtained and stored")
            return True

        except Exception as e:
            logger.error(f"Login request failed: {e}")
            return False

    def get(self, url: str, max_retries: int = 1, **kwargs) -> Optional['Response']:
        """Perform GET request with authenticated session.

        Args:
            url: URL or path to fetch (relative to base_url)
            max_retries: Number of retries after solving Akamai challenge (default: 1)
            **kwargs: Additional arguments passed to Session.get()

        Returns:
            Response object if successful, None if request failed

        Notes:
            - Automatically prefixes relative URLs with base_url
            - Uses persistent session with cookies
            - Auto-solves Akamai JS challenge if detected
        """
        # Build full URL if relative path provided
        if url.startswith('http'):
            full_url = url
        else:
            full_url = f"{self.base_url}{url}"

        logger.debug(f"GET {full_url}")

        attempt = 0
        while attempt <= max_retries:
            try:
                response = self.session.get(full_url, **kwargs)

                # Check for Akamai challenge (HTML with bm-verify)
                if response.status_code == 200:
                    ct = response.headers.get('Content-Type', '') or ''
                    ct_str = str(ct)
                    # Only check for challenge if response is HTML (not JSON)
                    if 'text/html' in ct_str and self._has_akamai_challenge(response.text):
                        if attempt >= max_retries:
                            logger.error(f"GET request failed: max retries exceeded for {full_url}")
                            return None
                        logger.info(f"Detected Akamai challenge on {full_url}, solving...")
                        if not self._solve_challenge(response.text, full_url):
                            logger.error("Failed to solve Akamai challenge")
                            return None
                        attempt += 1
                        continue  # retry the original request

                if response.status_code >= 400:
                    logger.error(f"GET request failed with status {response.status_code}")
                    return None
                return response
            except Exception as e:
                logger.error(f"GET request failed: {e}")
                return None

    def _has_akamai_challenge(self, html: str) -> bool:
        """Check if response HTML contains Akamai challenge.

        Args:
            html: HTML content to check

        Returns:
            True if Akamai bm-verify challenge detected
        """
        if not isinstance(html, str):
            return False
        if '<meta http-equiv="refresh"' not in html:
            return False
        if 'bm-verify=' not in html:
            return False
        return True

    def _solve_challenge(self, challenge_html: str, original_url: str) -> bool:
        """Solve Akamai challenge by following meta-refresh.

        Args:
            challenge_html: HTML containing the challenge meta-refresh
            original_url: Original URL that triggered the challenge

        Returns:
            True if challenge solved successfully, False otherwise
        """
        try:
            soup = BeautifulSoup(challenge_html, 'lxml')
            meta = soup.find('meta', attrs={'http-equiv': 'refresh'})
            if not meta:
                logger.error("No meta refresh found in challenge page")
                return False

            content = meta.get('content', '')
            # Extract URL from content like: "5; URL='...bm-verify=...'"
            match = re.search(r"URL='([^']+)'", content)
            if not match:
                logger.error("No bm-verify URL found in meta refresh")
                return False

            verify_url = match.group(1)
            # Make absolute URL
            if verify_url.startswith('/'):
                verify_url = f"{self.base_url}{verify_url}"
            elif not verify_url.startswith('http'):
                verify_url = f"{self.base_url}/{verify_url}"

            logger.info(f"Following Akamai challenge to: {verify_url[:80]}...")

            # Wait 2 seconds as browser would
            time.sleep(2)

            # Fetch the challenge verification URL
            verify_resp = self.session.get(verify_url, timeout=30)
            if verify_resp.status_code != 200:
                logger.error(f"Challenge verification failed: {verify_resp.status_code}")
                return False

            # Check if challenge cleared (should get real content now)
            if 'text/html' in verify_resp.headers.get('Content-Type', ''):
                if self._has_akamai_challenge(verify_resp.text):
                    logger.warning("Challenge still present after verification")
                    return False

            logger.info("Akamai challenge solved successfully")
            return True

        except Exception as e:
            logger.error(f"Challenge solving failed: {e}")
            return False

    def post(self, url: str, json: Optional[dict] = None, **kwargs) -> Optional['Response']:
        """Perform POST request with authenticated session.

        Args:
            url: URL or path for POST (relative to base_url)
            json: JSON data to POST (application/json)
            **kwargs: Additional arguments passed to Session.post()

        Returns:
            Response object if successful, None if request failed
        """
        # Build full URL if relative path provided
        if url.startswith('http'):
            full_url = url
        else:
            full_url = f"{self.base_url}{url}"

        logger.debug(f"POST {full_url}")

        try:
            response = self.session.post(full_url, json=json, **kwargs)
            if response.status_code >= 400:
                logger.error(f"POST request failed with status {response.status_code}")
                return None
            return response
        except Exception as e:
            logger.error(f"POST request failed: {e}")
            return None

    def close(self):
        """Close the session and release connections.

        Should be called when done with the session to properly
        clean up connection pool resources.

        Notes:
            - Sets logged_in = False after closing
            - Safe to call multiple times
        """
        logger.debug("Closing session")
        self.session.close()
        self.logged_in = False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures session is closed."""
        self.close()
