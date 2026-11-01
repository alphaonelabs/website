# Importing necessary modules for testing and mocking
# from unittest.mock import patch
# import requests
# from django.core.cache import cache
# from django.test import TestCase
# from web.social import NitterClient

# # Mock response class to simulate requests responses
# class MockResponse:
#     def __init__(self, text, status_code=200):
#         self.text = text
#         self.status_code = status_code

#     def raise_for_status(self):
#         if self.status_code >= 400:
#             raise requests.exceptions.HTTPError(f"HTTP Error: {self.status_code}")

# # Test case for NitterClient
# class TestNitterClient(TestCase):
#     def setUp(self):
#         self.username = "testuser"
#         self.client = NitterClient(self.username)
#         # Clear cache before each test
#         cache.clear()

#     def tearDown(self):
#         # Clear cache after each test
#         cache.clear()

#     def test_init(self):
#         """Test NitterClient initialization"""
#         self.assertEqual(self.client.username, self.username)
#         self.assertIsInstance(self.client.working_instances, list)

#     def test_is_valid_response(self):
#         """Test response validation"""
#         # Valid response
#         valid_html = """
#         <div class="profile-card">
#             <div class="profile-stat-num">1234</div>
#         </div>
#         """
#         self.assertTrue(self.client._is_valid_response(valid_html))

#         # Invalid response
#         invalid_html = "<div>Some other content</div>"
#         self.assertFalse(self.client._is_valid_response(invalid_html))

#     @patch("requests.get")
#     def test_find_working_instances(self, mock_get):
#         """Test finding working Nitter instances"""
#         valid_response = MockResponse(
#             """
#             <div class="profile-card">
#                 <div class="profile-stat-num">1234</div>
#             </div>
#             """
#         )
#         mock_get.return_value = valid_response

#         self.client._find_working_instances()
#         self.assertTrue(len(self.client.working_instances) > 0)
#         self.assertIsNotNone(self.client.base_url)

#     @patch("requests.get")
#     def test_find_working_instances_all_fail(self, mock_get):
#         """Test behavior when all instances fail"""
#         mock_get.side_effect = requests.exceptions.RequestException("Connection failed")

#         self.client._find_working_instances()
#         self.assertEqual(len(self.client.working_instances), 0)
#         self.assertIsNone(self.client.base_url)

#     @patch("requests.get")
#     def test_get_profile_stats_success(self, mock_get):
#         """Test successful profile stats retrieval"""
#         mock_response = """
#         <div class="profile-card">
#             <div class="profile-card-fullname">Test User</div>
#             <div class="profile-bio">Test bio</div>
#             <div class="profile-location">Test location</div>
#             <div class="profile-website"><a href="https://test.com">test.com</a></div>
#             <div class="profile-joindate">Joined January 2020</div>
#             <div class="followers">
#                 <span class="profile-stat-header">Followers</span>
#                 <span class="profile-stat-num">1000</span>
#             </div>
#             <div class="following">
#                 <span class="profile-stat-header">Following</span>
#                 <span class="profile-stat-num">500</span>
#             </div>
#             <div class="tweets">
#                 <span class="profile-stat-header">Posts</span>
#                 <span class="profile-stat-num">2000</span>
#             </div>
#             <div class="tweet-date" title="Jan 1, 2024 · 12:00 PM UTC">1h</div>
#         </div>
#         """
#         # Mock successful responses for both instance finding and stats retrieval
#         mock_get.return_value = MockResponse(mock_response)

#         # Get stats
#         stats = self.client.get_profile_stats()

#         self.assertIsNotNone(stats)
#         self.assertEqual(stats["name"], "Test User")
#         self.assertEqual(stats["bio"], "Test bio")
#         self.assertEqual(stats["location"], "Test location")
#         self.assertEqual(stats["website"], "https://test.com")
#         self.assertEqual(stats["followers"], 1000)
#         self.assertEqual(stats["following"], 500)
#         self.assertEqual(stats["tweets"], 2000)
#         self.assertIsNotNone(stats["last_tweet"])
#         self.assertIsNone(stats["error"])

#     @patch("requests.get")
#     def test_get_profile_stats_failure(self, mock_get):
#         """Test profile stats retrieval failure"""
#         mock_get.side_effect = requests.exceptions.RequestException("Connection failed")

#         stats = self.client.get_profile_stats()

#         self.assertIsNotNone(stats)
#         self.assertEqual(stats["followers"], 0)
#         self.assertEqual(stats["following"], 0)
#         self.assertEqual(stats["tweets"], 0)
#         self.assertIsNotNone(stats["error"])

#     def test_get_profile_stats_cached(self):
#         """Test cached profile stats retrieval"""
#         cached_stats = {"name": "Cached User", "followers": 100, "following": 50, "tweets": 200, "error": None}
#         cache_key = f"nitter_stats_{self.username}"
#         cache.set(cache_key, cached_stats, timeout=300)

#         stats = self.client.get_profile_stats()

#         self.assertEqual(stats, cached_stats)

#     @patch("requests.get")
#     def test_invalid_response_format(self, mock_get):
#         """Test handling of invalid response format"""
#         mock_get.return_value = MockResponse("<div>Invalid format</div>")

#         stats = self.client.get_profile_stats()

#         self.assertIsNotNone(stats["error"])
#         self.assertEqual(stats["followers"], 0)

#     @patch("requests.get")
#     def test_ssl_error_handling(self, mock_get):
#         """Test handling of SSL errors"""
#         mock_get.side_effect = requests.exceptions.SSLError("SSL verification failed")

#         stats = self.client.get_profile_stats()

#         self.assertIsNotNone(stats["error"])
#         self.assertEqual(stats["followers"], 0)

#     @patch("requests.get")
#     def test_timeout_handling(self, mock_get):
#         """Test handling of timeout errors"""
#         mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

#         stats = self.client.get_profile_stats()

#         self.assertIsNotNone(stats["error"])
#         self.assertEqual(stats["followers"], 0)

#     @patch("requests.get")
#     def test_connection_error_handling(self, mock_get):
#         """Test handling of connection errors"""
#         mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

#         stats = self.client.get_profile_stats()

#         self.assertIsNotNone(stats["error"])
#         self.assertEqual(stats["followers"], 0)

#     def test_retry_mechanism(self):
#         """Test the retry mechanism"""
#         valid_response = """
#         <div class="profile-card">
#             <div class="profile-card-info">
#                 <div class="profile-card-fullname">Test User</div>
#             </div>
#             <div class="profile-card-extra">
#                 <div class="profile-bio">Test bio</div>
#                 <div class="profile-website"><a href="https://test.com">test.com</a></div>
#                 <div class="profile-joindate">Joined January 2020</div>
#             </div>
#             <div class="profile-stats">
#                 <div class="followers">
#                     <span class="profile-stat-header">Followers</span>
#                     <span class="profile-stat-num">1000</span>
#                 </div>
#                 <div class="following">
#                     <span class="profile-stat-header">Following</span>
#                     <span class="profile-stat-num">500</span>
#                 </div>
#                 <div class="tweets">
#                     <span class="profile-stat-header">Posts</span>
#                     <span class="profile-stat-num">2000</span>
#                 </div>
#             </div>
#         </div>
#         """

#         # Create a custom side effect function that returns different responses based on the URL
#         def mock_get_side_effect(url, **kwargs):
#             # For instance finding, always return success
#             if any(instance in url for instance in self.client.NITTER_INSTANCES):
#                 if "First failure" in url or "Second failure" in url:
#                     raise requests.exceptions.RequestException(url.split("/")[-1])
#                 return MockResponse(valid_response)
#             return MockResponse(valid_response)

#         # Set up the client with working instances to avoid the instance finding process
#         self.client.working_instances = ["https://nitter.net", "https://nitter.pw"]
#         self.client.base_url = "https://nitter.net"

#         # Mock the requests.get method with our custom side effect
#         with patch("requests.get") as mock_get:
#             mock_get.side_effect = mock_get_side_effect

#             # Override the base_url to trigger our specific mock responses
#             self.client.base_url = "https://First failure"

#             # Get stats (this should trigger the retry mechanism)
#             stats = self.client.get_profile_stats()

#             # Verify the stats were retrieved successfully
#             self.assertIsNone(stats.get("error"))
#             self.assertEqual(stats["name"], "Test User")
#             self.assertEqual(stats["followers"], 1000)
#             self.assertEqual(stats["following"], 500)
#             self.assertEqual(stats["tweets"], 2000)

#     def test_user_agent_rotation(self):
#         """Test that user agents are properly rotated"""
#         self.assertGreater(len(self.client.USER_AGENTS), 1)
#         self.assertIsInstance(self.client.USER_AGENTS, list)
#         for agent in self.client.USER_AGENTS:
#             self.assertIsInstance(agent, str)
#             self.assertGreater(len(agent), 0)

#     def test_nitter_instances_validity(self):
#         """Test that all Nitter instances are valid URLs"""
#         for instance in self.client.NITTER_INSTANCES:
#             self.assertTrue(instance.startswith("https://"))
#             self.assertTrue("." in instance)  # Basic domain validation
