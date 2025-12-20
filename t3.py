#!/usr/bin/env python3
"""
ULTIMATE FACEBOOK COMMENT BOT - Hybrid Edition
Combines Graph API (professional) + Web methods (fallback)
"""

import re
import json
import time
import uuid
import random
import base64
import requests
from typing import Dict, Tuple, List, Optional
from urllib.parse import quote
import concurrent.futures
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


class HybridFacebookBot:
    """HYBRID Facebook bot - Uses Graph API first, falls back to web"""

    def __init__(self, cookie_string: str):
        """
        Initialize with multiple auth methods
        """
        # Parse cookie
        self.cookies = self._parse_cookies(cookie_string)
        self.user_id = self.cookies.get('c_user')

        if not self.user_id:
            raise ValueError("No c_user found in cookies")

        logger.info(f"🚀 Initializing HYBRID bot for user: {self.user_id}")

        # Session
        self.session = requests.Session()
        self.session.cookies.update(self.cookies)

        # Authentication methods
        self.fb_dtsg = None      # Web token (fallback)
        self.eaag_token = None   # Graph API token (preferred)
        self.page_tokens = {}    # Page-specific tokens

        # Initialize all auth methods
        self._initialize_all_auth()

    def _parse_cookies(self, cookie_string: str) -> Dict:
        """Parse cookie string"""
        cookies = {}
        for item in cookie_string.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key] = value
        return cookies

    def _initialize_all_auth(self):
        """Initialize ALL authentication methods"""
        logger.info("🔐 Initializing authentication methods...")

        # Method 1: Try EAAG token (Graph API - YOUR METHOD)
        logger.info("   Trying EAAG token (Graph API)...")
        eaag_success = self._get_eaag_token()

        if eaag_success:
            logger.info("✅ EAAG token obtained (Graph API ready)")

            # Get pages if EAAG token works
            pages = self._get_me_accounts()
            if pages:
                logger.info(f"✅ Found {len(pages)} pages via Graph API")
                self.page_tokens = pages
        else:
            logger.warning("⚠️ EAAG token failed")

        # Method 2: Get web token (fallback)
        logger.info("   Getting web token (fallback)...")
        self._get_web_token()

        if self.fb_dtsg:
            logger.info("✅ Web token obtained (fallback ready)")

        # Check if we have at least one auth method
        if not self.eaag_token and not self.fb_dtsg:
            logger.error("❌ All auth methods failed!")
            raise ValueError("Could not authenticate with Facebook")

    def _get_eaag_token(self) -> bool:
        """Get EAAG token from business.facebook.com (YOUR METHOD)"""
        try:
            url = "https://business.facebook.com/business_locations"
            response = self.session.get(url, timeout=10)
            match = re.search(r'(\["EAAG\w+)', response.text)

            if match:
                token = match.group(1).replace('["', '')
                self.eaag_token = token
                return True
        except Exception as e:
            logger.warning(f"EAAG token failed: {e}")

        return False

    def _get_web_token(self):
        """Get web token (fb_dtsg) - fallback method"""
        try:
            response = self.session.get(
                'https://www.facebook.com/?sk=h_chr', timeout=10)
            html = response.text

            # Try multiple patterns
            patterns = [
                r'"DTSGInitData",\[\],{"token":"([^"]+)"',
                r'name="fb_dtsg" value="([^"]+)"',
                r'"fb_dtsg":"([^"]+)"',
            ]

            for pattern in patterns:
                match = re.search(pattern, html)
                if match:
                    self.fb_dtsg = match.group(1)
                    break
        except Exception as e:
            logger.warning(f"Web token failed: {e}")

    def _get_me_accounts(self) -> Dict:
        """Get /me/accounts via Graph API (YOUR METHOD)"""
        if not self.eaag_token:
            return {}

        try:
            url = f"https://graph.facebook.com/me/accounts?access_token={self.eaag_token}"
            response = self.session.get(url, timeout=10)
            data = response.json()

            if "data" in data:
                pages = {}
                for account in data["data"]:
                    page_id = account["id"]
                    pages[page_id] = {
                        "name": account.get("name", f"Page {page_id}"),
                        "access_token": account.get("access_token", ""),
                        "category": account.get("category", ""),
                    }
                return pages
        except Exception as e:
            logger.warning(f"Failed to get /me/accounts: {e}")

        return {}

    def extract_post_id(self, post_url: str) -> Optional[str]:
        """Extract post ID from URL"""
        patterns = [
            r'/posts/(\d+)',
            r'story_fbid=(\d+)',
            r'fbid=(\d+)',
            r'(\d{15,})',
        ]

        for pattern in patterns:
            match = re.search(pattern, post_url)
            if match:
                return match.group(1)
        return None

    def post_comment_hybrid(self, post_url: str, comment_text: str,
                            use_page: str = None, attempt_num: int = 1) -> Tuple[bool, str, float]:
        """
        HYBRID comment posting - tries multiple methods

        Returns: (success, result, elapsed_time)
        """
        start_time = time.time()

        # Extract post ID
        post_id = self.extract_post_id(post_url)
        if not post_id:
            return False, "Invalid post URL", time.time() - start_time

        # Add variation
        if attempt_num > 1:
            emojis = ['👍', '😊', '🙏', '🔥', '⭐']
            comment_text = f"{comment_text} {random.choice(emojis)}"

        logger.debug(f"Posting comment {attempt_num} to post {post_id}")

        # METHOD 1: Graph API with EAAG token (PREFERRED)
        if self.eaag_token and (not use_page or use_page in self.page_tokens):
            success, result = self._post_via_graph_api(
                post_id, comment_text, use_page)
            if success:
                elapsed = time.time() - start_time
                return True, f"GraphAPI:{result}", elapsed

        # METHOD 2: Web GraphQL (fallback)
        if self.fb_dtsg:
            success, result = self._post_via_web_graphql(
                post_id, comment_text, use_page)
            if success:
                elapsed = time.time() - start_time
                return True, f"WebAPI:{result}", elapsed

        # METHOD 3: Web form (last resort)
        success, result = self._post_via_web_form(
            post_id, comment_text, use_page)
        elapsed = time.time() - start_time

        if success:
            return True, f"WebForm:{result}", elapsed
        else:
            return False, f"All methods failed", elapsed

    def _post_via_graph_api(self, post_id: str, comment_text: str, use_page: str = None) -> Tuple[bool, str]:
        """Post via Graph API (YOUR METHOD - preferred)"""
        try:
            # Determine which token to use
            if use_page and use_page in self.page_tokens:
                # Use page token
                token = self.page_tokens[use_page]["access_token"]
                actor = use_page
            else:
                # Use main EAAG token
                token = self.eaag_token
                actor = self.user_id

            if not token:
                return False, "No token available"

            # URL encode the comment
            encoded_comment = quote(comment_text)
            url = f"https://graph.facebook.com/{post_id}/comments?message={encoded_comment}&access_token={token}"

            response = self.session.post(url, timeout=5)
            data = response.json()

            if "id" in data:
                comment_id = data["id"]
                return True, f"CommentID:{comment_id[:10]}..."

            error = data.get("error", {}).get("message", "Unknown")
            return False, f"GraphAPI Error: {error}"

        except Exception as e:
            return False, f"GraphAPI Exception: {str(e)[:30]}"

    def _post_via_web_graphql(self, post_id: str, comment_text: str, use_page: str = None) -> Tuple[bool, str]:
        """Post via web GraphQL (fallback)"""
        if not self.fb_dtsg:
            return False, "No web token"

        try:
            feedback_id = base64.b64encode(
                f"feedback:{post_id}".encode()).decode()

            # Determine actor
            actor_id = use_page if use_page else self.user_id

            data = {
                'av': actor_id,
                '__user': actor_id,
                '__a': '1',
                '__req': '1',
                'fb_dtsg': self.fb_dtsg,
                'jazoest': str(sum(ord(c) for c in self.fb_dtsg) % 100000),
                'variables': json.dumps({
                    "input": {
                        "feedback_id": feedback_id,
                        "message": {"text": comment_text},
                        "actor_id": actor_id,
                        "client_mutation_id": str(uuid.uuid4())[:8],
                    },
                    "scale": 1,
                }),
                'doc_id': '24615176934823390',  # Working doc_id
            }

            response = self.session.post(
                'https://www.facebook.com/api/graphql/',
                data=data,
                timeout=5
            )

            if response.status_code == 200 and '"comment_create"' in response.text:
                return True, "Success"

            return False, f"HTTP:{response.status_code}"

        except Exception as e:
            return False, f"WebGraphQL: {str(e)[:30]}"

    def _post_via_web_form(self, post_id: str, comment_text: str, use_page: str = None) -> Tuple[bool, str]:
        """Post via web form (last resort)"""
        if not self.fb_dtsg:
            return False, "No web token"

        try:
            # Get post page
            post_page = f"https://www.facebook.com/story.php?story_fbid={post_id}"
            response = self.session.get(post_page, timeout=5)

            # Try to find form
            form_match = re.search(
                r'action="([^"]*comment/render[^"]*)"', response.text)
            if form_match:
                form_url = form_match.group(1)
                if form_url.startswith('/'):
                    form_url = f"https://www.facebook.com{form_url}"

                # Prepare form data
                form_data = {
                    'fb_dtsg': self.fb_dtsg,
                    'comment_text': comment_text,
                    'ft_ent_identifier': post_id,
                }

                # Submit
                response = self.session.post(
                    form_url, data=form_data, timeout=5)
                if response.status_code == 200:
                    return True, "FormSuccess"

            return False, "FormNotFound"

        except Exception as e:
            return False, f"WebForm: {str(e)[:30]}"

    def rapid_comments_hybrid(self, post_url: str, comment_text: str,
                              count: int = 3, use_pages: bool = False) -> Dict:
        """
        Rapid commenting with HYBRID approach

        Args:
            post_url: Post URL
            comment_text: Comment text
            count: Number of comments
            use_pages: Whether to use available pages

        Returns:
            Results dictionary
        """
        logger.info("=" * 70)
        logger.info("💥 HYBRID RAPID COMMENT BOT")
        logger.info("=" * 70)
        logger.info(f"User: {self.user_id}")
        logger.info(
            f"Auth methods: {'EAAG✓ ' if self.eaag_token else ''}{'Web✓ ' if self.fb_dtsg else ''}")
        logger.info(f"Pages available: {len(self.page_tokens)}")
        logger.info(f"Target: {count} comments")
        logger.info("=" * 70)

        # Prepare profiles to post from
        profiles = []

        # Add main user
        profiles.append({
            "id": self.user_id,
            "name": "Main User",
            "type": "user",
            "token_type": "EAAG" if self.eaag_token else "Web"
        })

        # Add pages if requested and available
        if use_pages and self.page_tokens:
            for page_id, page_info in self.page_tokens.items():
                profiles.append({
                    "id": page_id,
                    "name": page_info["name"],
                    "type": "page",
                    "token_type": "PageToken"
                })

        logger.info(f"Posting from {len(profiles)} profiles")

        results = []
        successful = 0
        start_time = time.time()

        # Distribute comments among profiles
        comments_per_profile = max(1, count // len(profiles))
        extra_comments = count % len(profiles)

        for profile_idx, profile in enumerate(profiles):
            profile_comments = comments_per_profile + \
                (1 if profile_idx < extra_comments else 0)

            if profile_comments == 0:
                continue

            logger.info(
                f"\n📄 {profile['name']} ({profile['type']}): {profile_comments} comments")

            for i in range(profile_comments):
                comment_num = len(results) + 1
                logger.info(f"  → Comment {comment_num}/{count}")

                # Post comment
                success, result, elapsed = self.post_comment_hybrid(
                    post_url=post_url,
                    comment_text=comment_text,
                    use_page=profile["id"] if profile["type"] == "page" else None,
                    attempt_num=comment_num
                )

                if success:
                    logger.info(f"    ✅ {result} ({elapsed:.3f}s)")
                    successful += 1
                else:
                    logger.info(f"    ❌ {result} ({elapsed:.3f}s)")

                results.append({
                    "profile": profile["name"],
                    "type": profile["type"],
                    "attempt": comment_num,
                    "success": success,
                    "result": result,
                    "elapsed": elapsed,
                    "timestamp": time.time()
                })

                # Ultra-fast delay between comments (50-200ms)
                if comment_num < count:
                    delay = random.uniform(0.05, 0.2)
                    time.sleep(delay)

        # Calculate statistics
        total_time = time.time() - start_time

        logger.info("\n" + "=" * 70)
        logger.info("📊 PERFORMANCE RESULTS")
        logger.info("=" * 70)
        logger.info(f"✅ Successful: {successful}/{count}")
        logger.info(f"⏱️  Total time: {total_time:.2f}s")

        if successful > 0:
            speed = successful / total_time
            logger.info(f"⚡ Speed: {speed:.2f} comments/second")

            if speed >= 3:
                logger.info(
                    f"🏆 TARGET ACHIEVED: {speed:.1f} ≥ 3 comments/second!")
            else:
                logger.info(
                    f"⚠️ Below target: {speed:.1f} < 3 comments/second")

        logger.info("=" * 70)

        # Detailed breakdown
        logger.info("\n📈 DETAILED BREAKDOWN:")
        for profile in profiles:
            profile_results = [
                r for r in results if r["profile"] == profile["name"]]
            profile_success = sum(1 for r in profile_results if r["success"])
            logger.info(
                f"  {profile['name']}: {profile_success}/{len(profile_results)} successful")

        return {
            "status": "completed",
            "successful": successful,
            "total": count,
            "speed": round(successful / max(0.1, total_time), 2),
            "total_time": round(total_time, 3),
            "profiles_used": len(profiles),
            "results": results
        }

# Thread wrapper for your existing code


class HybridCommentThread:
    """Thread wrapper for HYBRID bot"""

    def __init__(self, cookie, post_link, comment, comment_per_acc, result_container, use_pages=False):
        self.cookie_str = list(cookie.keys())[0]
        self.post_link = post_link
        self.comment = comment
        self.comment_per_acc = comment_per_acc
        self.result_container = result_container
        self.use_pages = use_pages
        self.results = None

    def run(self):
        """Run hybrid comments"""
        try:
            bot = HybridFacebookBot(self.cookie_str)

            # Run rapid comments
            self.results = bot.rapid_comments_hybrid(
                post_url=self.post_link,
                comment_text=self.comment,
                count=self.comment_per_acc,
                use_pages=self.use_pages
            )

            # Update result container
            for result in self.results["results"]:
                if result["success"]:
                    self.result_container['success'].append({
                        'profile': result["profile"],
                        'type': result["type"],
                        'attempt': result["attempt"],
                        'result': result["result"],
                        'elapsed': result["elapsed"],
                        'timestamp': result["timestamp"]
                    })
                else:
                    self.result_container['failure'].append({
                        'profile': result["profile"],
                        'type': result["type"],
                        'attempt': result["attempt"],
                        'error': result["result"],
                        'timestamp': result["timestamp"]
                    })

        except Exception as e:
            self.result_container['failure'].append({
                'error': str(e),
                'timestamp': time.time()
            })

# Simple test function


def test_hybrid_bot():
    """Test the hybrid bot"""

    COOKIE_STRING = "datr=SK8maRcMTTI5l5jYA2lNg9Vn; fr=10DTXgNJyOhjXXbVl.AWeWqJ_2gegQvWxTZiom95bjeXBPptBTlF70DcjGHpH3AM3dQ-A.BpRmyz..AAA.0.0.BpRmyz.AWdLi3KMi0AE8WbFy3tk_NlpQ1w; sb=SK8maQT5FcoNhX1ii3_svYfg; locale=en_US; wd=588x479; dpr=1.6800000667572021; ps_l=1; ps_n=1; c_user=100086111536900; xs=4%3AhEP3GPso2CzlRA%3A2%3A1766136688%3A-1%3A-1%3A%3AAczQc-ROIT3b9-QsJ-ly1BG_JahRSenkLut1oe9Jcw; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1766223040399%2C%22v%22%3A1%7D"
    POST_URL = "https://www.facebook.com/100068994467075/posts/534891072154037/"

    print("=" * 70)
    print("🚀 HYBRID FACEBOOK COMMENT BOT TEST")
    print("=" * 70)

    try:
        # Create bot
        bot = HybridFacebookBot(COOKIE_STRING)

        print(f"✅ Bot initialized")
        print(f"   User: {bot.user_id}")
        print(f"   EAAG Token: {'Yes' if bot.eaag_token else 'No'}")
        print(f"   Web Token: {'Yes' if bot.fb_dtsg else 'No'}")
        print(f"   Pages: {len(bot.page_tokens)}")

        # Test single comment
        print("\n🧪 Testing single comment...")
        success, result, elapsed = bot.post_comment_hybrid(
            post_url=POST_URL,
            comment_text="Hybrid bot test comment!",
            attempt_num=1
        )

        if success:
            print(f"✅ Single comment: {result} ({elapsed:.3f}s)")

            # Run rapid comments
            print("\n" + "=" * 70)
            print("🚀 STARTING RAPID COMMENTS (3 comments)")
            print("=" * 70)

            results = bot.rapid_comments_hybrid(
                post_url=POST_URL,
                comment_text="Hybrid rapid comment",
                count=3,
                use_pages=True  # Use pages if available
            )

            # Summary
            print("\n🎯 FINAL RESULTS:")
            print(f"✅ Successful: {results['successful']}/3")
            print(f"⚡ Speed: {results['speed']} comments/second")
            print(f"⏱️  Time: {results['total_time']}s")

            if results['speed'] >= 3:
                print("🏆 TARGET ACHIEVED! 3+ comments/second")
            else:
                print(
                    f"⚠️ Below target: {results['speed']:.1f} comments/second")

        else:
            print(f"❌ Single comment failed: {result}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_hybrid_bot()
