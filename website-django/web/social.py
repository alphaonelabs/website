import logging
import random
import re
from datetime import datetime

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class NitterClient:
    """Client for fetching Twitter/X data via Nitter."""

    # List of Nitter instances to try in case of failure
    NITTER_INSTANCES = [
        "https://nitter.net",
        "https://nitter.lacontrevoie.fr",
        "https://nitter.nixnet.services",
        "https://nitter.pw",
        "https://nitter.poast.org",
        "https://nitter.d420.de",
        "https://nitter.platypush.tech",
        "https://nitter.sethforprivacy.com",
        "https://nitter.cutelab.space",
        "https://nitter.ktachibana.party",
    ]

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 " "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    ]

    def __init__(self, username):
        self.username = username
        self.base_url = None
        self.working_instances = []
        self._find_working_instances()

    def _is_valid_response(self, response_text):
        """Check if the response contains valid profile data."""
        # More lenient validation to handle different Nitter instance formats
        required_elements = [
            'class="profile-card"',
            'class="profile-stat-num"',
        ]
        return any(element in response_text for element in required_elements)

    def _find_working_instances(self):
        """Try all Nitter instances and collect working ones."""
        random.shuffle(self.NITTER_INSTANCES)  # Randomize the order to distribute load

        for instance in self.NITTER_INSTANCES:
            try:
                headers = {
                    "User-Agent": random.choice(self.USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }

                # Try fetching the profile directly with a shorter timeout
                response = requests.get(
                    f"{instance}/{self.username}",
                    headers=headers,
                    timeout=5,  # Reduced timeout to fail faster
                    allow_redirects=True,
                    verify=True,  # Always verify SSL for security
                )
                response.raise_for_status()

                if self._is_valid_response(response.text):
                    logger.info(f"Found working Nitter instance: {instance}")
                    self.working_instances.append(instance)
                    if not self.base_url:
                        self.base_url = instance

            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to connect to Nitter instance {instance}: {str(e)}")
                continue
            except Exception as e:
                logger.warning(f"Unexpected error with {instance}: {str(e)}")
                continue

            # Break after finding 2 working instances to avoid unnecessary checks
            if len(self.working_instances) >= 2:
                break

        if not self.working_instances:
            logger.error("No working Nitter instances found")
            logger.error("Tried instances: " + ", ".join(self.NITTER_INSTANCES))

    def get_working_instance(self):
        """Get a working instance, trying to find new ones if necessary."""
        if not self.working_instances:
            self._find_working_instances()

        if self.working_instances:
            self.base_url = random.choice(self.working_instances)
            return self.base_url
        return None

    def get_profile_stats(self):
        """
        Fetch profile statistics from Nitter.
        Returns dict with followers, following, tweets count, and last tweet info.
        """
        if not self.base_url:
            self.base_url = self.get_working_instance()
            if not self.base_url:
                # Return cached data if available
                cache_key = f"nitter_stats_{self.username}"
                cached_data = cache.get(cache_key)
                if cached_data:
                    logger.info("Using cached data due to Nitter unavailability")
                    return cached_data
                return self._get_error_stats("No working Nitter instance available - using fallback data")

        cache_key = f"nitter_stats_{self.username}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data

        max_retries = 3
        retry_count = 0
        last_error = None

        # Store original base_url to restore if needed
        original_base_url = self.base_url

        while retry_count < max_retries:
            try:
                logger.debug(f"Attempt {retry_count + 1}: Fetching stats from {self.base_url}")

                headers = {
                    "User-Agent": random.choice(self.USER_AGENTS),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                }

                response = requests.get(
                    f"{self.base_url}/{self.username}",
                    headers=headers,
                    timeout=10,
                    allow_redirects=True,
                    verify=True,  # Always verify SSL for security
                )
                response.raise_for_status()

                if not self._is_valid_response(response.text):
                    raise ValueError("Invalid response format")

                stats = self._parse_profile_stats(response.text)

                if stats.get("error"):
                    raise ValueError(stats["error"])

                # Cache the results for 30 minutes
                cache.set(cache_key, stats, timeout=1800)
                return stats

            except (requests.exceptions.RequestException, ValueError) as e:
                last_error = str(e)
                logger.warning(f"Attempt {retry_count + 1} failed: {last_error}")

                # Increment retry count
                retry_count += 1

                # Try another instance if we have retries left
                if retry_count < max_retries:
                    # Remove the current instance from working instances if it failed
                    if self.base_url in self.working_instances:
                        self.working_instances.remove(self.base_url)

                    # Get a new working instance
                    new_base_url = self.get_working_instance()
                    if new_base_url:
                        self.base_url = new_base_url
                        logger.debug(f"Switching to alternate instance: {self.base_url}")
                    else:
                        # If no new instance is available, restore the original and break
                        self.base_url = original_base_url
                        break
                else:
                    # We've exhausted our retries
                    break

        # If all retries failed, try to return cached data
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info("Using cached data after retries failed")
            return cached_data

        return self._get_error_stats("Failed to fetch stats - using fallback data")

    def _parse_profile_stats(self, html_content):
        """Parse the HTML content and extract profile stats."""
        stats = {
            "followers": 0,
            "following": 0,
            "tweets": 0,
            "engagement": 0,
            "last_tweet": None,
            "name": None,
            "bio": None,
            "location": None,
            "website": None,
            "joined": None,
            "error": None,
        }

        try:
            # Extract name
            name_pattern = r'class="profile-card-fullname"[^>]*>([^<]+)'
            name_match = re.search(name_pattern, html_content)
            if name_match:
                stats["name"] = name_match.group(1).strip()

            # Extract bio
            bio_pattern = r'class="profile-bio"[^>]*>([^<]+)'
            bio_match = re.search(bio_pattern, html_content)
            if bio_match:
                stats["bio"] = bio_match.group(1).strip()

            # Extract location
            location_pattern = r'class="profile-location"[^>]*>([^<]+)'
            location_match = re.search(location_pattern, html_content)
            if location_match:
                stats["location"] = location_match.group(1).strip()

            # Extract website - handle both direct and linked formats
            website_pattern = r'class="profile-website"[^>]*>(?:<a[^>]*href="([^"]+)"[^>]*>)?([^<]+)'
            website_match = re.search(website_pattern, html_content)
            if website_match:
                stats["website"] = website_match.group(1) if website_match.group(1) else website_match.group(2)

            # Extract joined date
            joined_pattern = r'class="profile-joindate"[^>]*>Joined ([^<]+)'
            joined_match = re.search(joined_pattern, html_content)
            if joined_match:
                try:
                    stats["joined"] = datetime.strptime(joined_match.group(1).strip(), "%B %Y")
                except ValueError:
                    pass

            # Extract follower count
            followers_pattern = r'class="followers"[^>]*>.*?class="profile-stat-num"[^>]*>([^<]+)'
            followers_match = re.search(followers_pattern, html_content, re.DOTALL)
            if followers_match:
                try:
                    stats["followers"] = int(followers_match.group(1).replace(",", ""))
                except ValueError:
                    pass

            # Extract following count
            following_pattern = r'class="following"[^>]*>.*?class="profile-stat-num"[^>]*>([^<]+)'
            following_match = re.search(following_pattern, html_content, re.DOTALL)
            if following_match:
                try:
                    stats["following"] = int(following_match.group(1).replace(",", ""))
                except ValueError:
                    pass

            # Extract tweets count
            tweets_pattern = r'class="tweets"[^>]*>.*?class="profile-stat-num"[^>]*>([^<]+)'
            tweets_match = re.search(tweets_pattern, html_content, re.DOTALL)
            if tweets_match:
                try:
                    stats["tweets"] = int(tweets_match.group(1).replace(",", ""))
                except ValueError:
                    pass

            # Extract last tweet date
            tweet_date_pattern = r'class="tweet-date"[^>]*title="([^"]+)"'
            tweet_date_match = re.search(tweet_date_pattern, html_content)
            if tweet_date_match:
                try:
                    stats["last_tweet"] = datetime.strptime(tweet_date_match.group(1).split(" · ")[0], "%b %d, %Y")
                except (ValueError, IndexError):
                    pass

            return stats

        except Exception as e:
            logger.error(f"Error parsing profile stats: {str(e)}")
            return self._get_error_stats(f"Error parsing Nitter stats: {str(e)}")

    def _get_error_stats(self, error_message):
        """Return a stats dict with error message and zero values."""
        return {
            "followers": 0,
            "following": 0,
            "tweets": 0,
            "engagement": 0,
            "last_tweet": None,
            "name": None,
            "bio": None,
            "location": None,
            "website": None,
            "joined": None,
            "error": error_message,
        }


def get_social_stats():
    """
    Get stats from all configured social media platforms.
    Returns dict with stats for each platform.
    """
    stats = {}

    # Get X/Twitter stats via Nitter
    if hasattr(settings, "TWITTER_USERNAME"):
        nitter = NitterClient(settings.TWITTER_USERNAME)
        x_stats = nitter.get_profile_stats()
        if x_stats:
            stats["x"] = {
                "stats": x_stats,
                "date": x_stats.get("last_tweet"),
                "status": "danger" if x_stats.get("error") else "success" if x_stats.get("last_tweet") else "neutral",
                "error": x_stats.get("error"),
            }

    # Add other social media platforms here as needed

    return stats
