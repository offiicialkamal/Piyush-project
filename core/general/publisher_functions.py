import re
import json
import time
import uuid
import random
import hashlib
import requests
from typing import Dict, Optional, Tuple, List
import threading


class FacebookMobileManager:
    """High-speed Facebook mobile comment manager"""

    def __init__(self, cookie_string: str, user_agent: str, result_container: Dict):
        self.cookies = self._parse_cookies(cookie_string)
        self.user_id = self.cookies.get('c_user')

        if not self.user_id:
            raise ValueError("No c_user found in cookies")

        # Mobile device configuration
        self.device_info = self._setup_mobile_device()

        # Session management
        self.session = requests.Session()
        self.session.cookies.update(self.cookies)

        # Token storage (fetched once, used many times)
        self.tokens = {}
        self.volatile_params = {}
        self.fb_dtsg = None

        # Profiles to post from
        self.all_profiles = {}
        self.result_container = result_container

        # Initialize session
        self._initialize_session()

    def _parse_cookies(self, cookie_string: str) -> Dict:
        """Parse cookie string to dictionary"""
        cookies = {}
        for item in cookie_string.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key] = value
        return cookies

    def _setup_mobile_device(self) -> Dict:
        """Configure mobile device parameters"""
        devices = [
            {
                'name': 'Samsung Galaxy S23',
                'model': 'SM-S911B',
                'user_agent': '[FBAN/FB4A;FBAV/434.0.0.35.114;FBBV/468570802;FBDM/{density=3.0,width=1080,height=2340};FBLC/en_US;FBRV/0;FBCR/AT&T;FBMF/samsung;FBBD/samsung;FBPN/com.facebook.katana;FBDV/SM-S911B;FBSV/13;FBOP/1;FBCA/arm64-v8a:]',
                'device_id': f"android-{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}",
                'locale': 'en_US',
                'network': 'WIFI',
            }
        ]
        return random.choice(devices)

    def _extract_from_html(self, html: str, patterns: List[str]) -> Optional[str]:
        """Extract value using regex patterns"""
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                return match.group(1)
        return None

    def _initialize_session(self):
        """Initialize session and fetch all tokens once"""
        print(f"📱 Initializing mobile session for user: {self.user_id}")

        # Mobile headers
        headers = {
            'User-Agent': self.device_info['user_agent'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'X-FB-Connection-Type': self.device_info['network'],
            'X-FB-Connection-Quality': 'EXCELLENT',
        }

        try:
            # Fetch homepage to get all tokens
            response = self.session.get(
                'https://m.facebook.com/home.php',
                headers=headers,
                timeout=10
            )

            if response.status_code != 200:
                print(f"⚠️ Failed to initialize: HTTP {response.status_code}")
                return

            html = response.text

            # Extract fb_dtsg (CRITICAL)
            fb_dtsg_patterns = [
                r'"DTSGInitData",\[\],{"token":"([^"]+)"',
                r'name="fb_dtsg" value="([^"]+)"',
                r'"token":"([^"]{20,200})"',
            ]
            self.fb_dtsg = self._extract_from_html(html, fb_dtsg_patterns)

            if not self.fb_dtsg:
                print("❌ Could not extract fb_dtsg")
                return

            # Store basic tokens
            self.tokens = {
                'fb_dtsg': self.fb_dtsg,
                'lsd': self._extract_from_html(html, [r'"lsd":"([^"]+)"']) or "AVqU5abc123",
                '__rev': self._extract_from_html(html, [r'"client_revision":(\d+)']) or "1031055084",
                '__user': self.user_id,
                'av': self.user_id,
            }

            # Extract volatile parameters (IMPORTANT FOR SPEED)
            self.volatile_params = {
                '__dyn': self._extract_from_html(html, [r'"__dyn":"([^"]+)"']),
                '__csr': self._extract_from_html(html, [r'"__csr":"([^"]+)"']),
                '__hsdp': self._extract_from_html(html, [r'"__hsdp":"([^"]+)"']),
                '__hblp': self._extract_from_html(html, [r'"__hblp":"([^"]+)"']),
                '__sjsp': self._extract_from_html(html, [r'"__sjsp":"([^"]+)"']),
            }

            # Generate jazoest from fb_dtsg
            self.tokens['jazoest'] = str(sum(ord(c)
                                         for c in self.fb_dtsg) % 100000)

            print(f"✅ Session initialized: {self.tokens['__rev']}")

        except Exception as e:
            print(f"⚠️ Session init error: {e}")

    def extract_post_info(self, post_url: str) -> Optional[Dict]:
        """Extract post ID and feedback ID from URL"""
        print(f"📱 Extracting post info: {post_url}")

        # Extract post ID
        patterns = [
            r'/posts/(\d+)',
            r'story_fbid=(\d+)',
            r'fbid=(\d+)',
            r'(\d{15,})',
        ]

        post_id = None
        for pattern in patterns:
            match = re.search(pattern, post_url)
            if match:
                post_id = match.group(1)
                break

        if not post_id:
            print("❌ Could not extract post ID")
            return None

        # Construct feedback ID (mobile format)
        import base64
        feedback_id = base64.b64encode(f"feedback:{post_id}".encode()).decode()

        return {
            'post_id': post_id,
            'feedback_id': feedback_id,
            'post_url': f"https://m.facebook.com/story.php?story_fbid={post_id}"
        }

    def post_comment_mobile(self, post_info: Dict, comment_text: str,
                            profile_id: str = None, is_page: bool = False) -> Tuple[bool, str]:
        """High-speed mobile comment posting"""

        if not self.fb_dtsg:
            return False, "Session not initialized"

        # Use page ID if provided, otherwise user ID
        actor_id = profile_id if is_page else self.user_id
        av_value = profile_id if is_page else self.user_id

        # Mobile GraphQL headers
        headers = {
            'User-Agent': self.device_info['user_agent'],
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-FB-Connection-Type': self.device_info['network'],
            'X-FB-Connection-Quality': 'EXCELLENT',
            'X-FB-Friendly-Name': 'CometUFIFeedbackReactMutation',
            'X-FB-HTTP-Engine': 'Liger',
            'X-FB-Client-IP': 'True',
            'Origin': 'https://www.facebook.com',
            'Referer': 'fb://facebook.com',
        }

        if is_page:
            headers['X-FB-Page-ID'] = profile_id

        # Generate unique IDs
        client_mutation_id = str(random.randint(1000000, 9999999))
        session_id = str(uuid.uuid4())

        # Mobile GraphQL data
        data = {
            'access_token': f"{self.user_id}|{self.cookies.get('xs', '')[:30]}",
            'av': av_value,
            '__user': actor_id,
            '__a': '1',
            '__req': '1',
            '__rev': self.tokens['__rev'],
            'fb_dtsg': self.fb_dtsg,
            'jazoest': self.tokens['jazoest'],
            'lsd': self.tokens['lsd'],
            'variables': json.dumps({
                "input": {
                    "actor_id": actor_id,
                    "feedback_id": post_info['feedback_id'],
                    "message": {
                        "text": comment_text,
                        "ranges": []
                    },
                    "attachments": [],
                    "tracking": [
                        json.dumps({
                            "app_id": "256002347743983",
                            "logging_id": f"mobile_{int(time.time())}",
                            "session_id": session_id,
                            "device_id": self.device_info['device_id'],
                        })
                    ],
                    "session_id": session_id,
                    "client_mutation_id": client_mutation_id,
                    "feedback_source": "MOBILE",
                    "feedback_referrer": "permalink",
                    "is_tracking_encrypted": True,
                    "idempotence_token": str(uuid.uuid4()),
                    "device_id": self.device_info['device_id'],
                },
                "scale": 1,
                "useDefaultActor": False,
            }),
            'server_timestamps': 'true',
            'doc_id': '5664991973387307',  # Mobile comment mutation
        }

        # Add volatile params if available
        if self.volatile_params.get('__dyn'):
            data['__dyn'] = self.volatile_params['__dyn']
            data['__csr'] = self.volatile_params.get('__csr', '')

        try:
            response = self.session.post(
                'https://www.facebook.com/api/graphql/',
                headers=headers,
                data=data,
                timeout=10
            )

            if response.status_code != 200:
                return False, f"HTTP {response.status_code}"

            # Parse response
            response_text = response.text
            if response_text.startswith("for (;;);"):
                response_text = response_text[9:]

            try:
                result = json.loads(response_text)

                if 'errors' in result:
                    error = result['errors'][0].get('message', 'Unknown error')
                    return False, error

                if 'data' in result:
                    data_node = result['data']
                    if 'comment_create' in data_node:
                        comment = data_node['comment_create'].get(
                            'comment', {})
                        comment_id = comment.get('id', '')
                        if comment_id:
                            return True, comment_id

                return False, "No comment ID in response"

            except json.JSONDecodeError:
                return False, "Invalid JSON response"

        except Exception as e:
            return False, f"Error: {str(e)}"

    def post_comments_fast(self, post_url: str, comment_text: str,
                           comments_per_profile: int = 1, delay_ms: int = 100) -> Dict:
        """
        High-speed comment posting with minimal delays

        Args:
            post_url: Facebook post URL
            comment_text: Comment to post
            comments_per_profile: Comments per account/page
            delay_ms: Delay between comments in milliseconds (default: 100ms = 0.1s)
        """

        print(f"🚀 Starting high-speed comment posting...")
        print(f"📱 Post: {post_url}")
        print(f"📱 Comments per profile: {comments_per_profile}")
        print(f"📱 Delay between comments: {delay_ms}ms")

        # Get post info
        post_info = self.extract_post_info(post_url)
        if not post_info:
            return {'status': 'error', 'error': 'Could not extract post info'}

        results = {
            'success': [],
            'failed': [],
            'total_success': 0,
            'total_failed': 0
        }

        # Add main user to profiles
        self.all_profiles[self.user_id] = {
            'id': self.user_id,
            'name': 'Main User',
            'type': 'user',
            'is_page': False
        }

        # Post from each profile
        for profile_id, profile_info in self.all_profiles.items():
            print(
                f"\n{'👤' if not profile_info['is_page'] else '📄'} {profile_info['name']}:")

            for i in range(comments_per_profile):
                # Add slight variation to avoid spam detection
                current_comment = comment_text
                if i > 0:
                    emojis = ['👍', '😊', '🙏', '🔥', '⭐', '💯']
                    current_comment = f"{comment_text} {random.choice(emojis)}"

                print(f"  → Comment {i+1}/{comments_per_profile}")

                # Post comment
                success, result = self.post_comment_mobile(
                    post_info=post_info,
                    comment_text=current_comment,
                    profile_id=profile_id,
                    is_page=profile_info['is_page']
                )

                if success:
                    print(f"    ✅ Success! ID: {result[:20]}...")
                    results['success'].append({
                        'profile': profile_info['name'],
                        'type': profile_info['type'],
                        'comment_id': result,
                        'timestamp': time.time()
                    })
                    results['total_success'] += 1
                else:
                    print(f"    ❌ Failed: {result}")
                    results['failed'].append({
                        'profile': profile_info['name'],
                        'type': profile_info['type'],
                        'error': result,
                        'timestamp': time.time()
                    })
                    results['total_failed'] += 1
                    break

                # Minimal delay between comments (can be as low as 50ms)
                if i < comments_per_profile - 1 and delay_ms > 0:
                    time.sleep(delay_ms / 1000.0)

        print(
            f"\n📊 Results: {results['total_success']} success, {results['total_failed']} failed")
        return results


# Thread wrapper for compatibility
class MobileFacebookThread(threading.Thread):
    def __init__(self, cookie_string: str, user_agent: str, post_link: str,
                 comment: str, comment_per_acc: int = 1, result_container: Dict = None):
        super().__init__()
        self.cookie_string = cookie_string
        self.user_agent = user_agent
        self.post_link = post_link
        self.comment = comment
        self.comment_per_acc = comment_per_acc
        self.result_container = result_container or {
            'success': [],
            'failure': [],
            'locked': []
        }
        self.results = None

    def run(self):
        """Run high-speed mobile bot"""
        try:
            manager = FacebookMobileManager(
                cookie_string=self.cookie_string,
                user_agent=self.user_agent,
                result_container=self.result_container
            )

            self.results = manager.post_comments_fast(
                post_url=self.post_link,
                comment_text=self.comment,
                comments_per_profile=self.comment_per_acc,
                delay_ms=100  # 100ms = 0.1s between comments
            )

        except Exception as e:
            self.results = {
                'status': 'error',
                'error': str(e)
            }


# Main function for backward compatibility
def run_mobile_facebook_comment(cookie_string: str, user_agent: str, post_link: str,
                                comment: str, comment_per_acc: int = 1, result_container: Dict = None):
    """Main function for high-speed mobile commenting"""

    if result_container is None:
        result_container = {
            'success': [],
            'failure': [],
            'locked': []
        }

    try:
        manager = FacebookMobileManager(
            cookie_string=cookie_string,
            user_agent=user_agent,
            result_container=result_container
        )

        results = manager.post_comments_fast(
            post_url=post_link,
            comment_text=comment,
            comments_per_profile=comment_per_acc,
            delay_ms=100  # Adjustable delay
        )

        return {
            'status': 'completed',
            'results': results,
            'user_id': manager.user_id
        }

    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }
