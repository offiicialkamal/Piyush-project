#!/usr/bin/env python3
"""
ULTIMATE FACEBOOK COMMENT BOT - Hybrid Multi-Threaded Edition
Parallel processing for maximum speed
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
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import logging
from queue import Queue
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class CommentResult:
    """Result of a comment attempt"""
    success: bool
    session_id: str
    profile_name: str
    profile_type: str
    attempt_num: int
    method: str
    comment_id: Optional[str] = None
    error: Optional[str] = None
    elapsed: float = 0.0


class FacebookSession:
    """Represents a single authenticated Facebook session"""

    def __init__(self, session_id: str, cookie_string: str):
        self.session_id = session_id
        self.cookies = self._parse_cookies(cookie_string)
        self.user_id = self.cookies.get('c_user')

        if not self.user_id:
            raise ValueError("No c_user found in cookies")

        # Session
        self.session = requests.Session()
        self.session.cookies.update(self.cookies)

        # Authentication
        self.fb_dtsg = None
        self.eaag_token = None
        self.page_tokens = {}
        self.profiles = []

        # Initialize
        self._initialize_auth()
        self._prepare_profiles()

    def _parse_cookies(self, cookie_string: str) -> Dict:
        """Parse cookie string"""
        cookies = {}
        for item in cookie_string.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key] = value
        return cookies

    def _initialize_auth(self):
        """Initialize authentication methods"""
        # EAAG Token
        try:
            url = "https://business.facebook.com/business_locations"
            response = self.session.get(url, timeout=10)
            match = re.search(r'(\["EAAG\w+)', response.text)
            if match:
                self.eaag_token = match.group(1).replace('["', '')
        except:
            pass

        # Web token
        try:
            response = self.session.get(
                'https://www.facebook.com/?sk=h_chr', timeout=10)
            html = response.text
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
        except:
            pass

        # Get pages if EAAG token exists
        if self.eaag_token:
            try:
                url = f"https://graph.facebook.com/me/accounts?access_token={self.eaag_token}"
                response = self.session.get(url, timeout=10)
                data = response.json()
                if "data" in data:
                    for account in data["data"]:
                        self.page_tokens[account["id"]] = {
                            "name": account.get("name", f"Page {account['id']}"),
                            "access_token": account.get("access_token", ""),
                            "category": account.get("category", ""),
                        }
            except:
                pass

    def _prepare_profiles(self):
        """Prepare list of available profiles"""
        # Add main user
        self.profiles.append({
            "id": self.user_id,
            "name": f"User_{self.user_id[:6]}",
            "type": "user",
            "token_type": "EAAG" if self.eaag_token else "Web"
        })

        # Add pages
        for page_id, page_info in self.page_tokens.items():
            self.profiles.append({
                "id": page_id,
                "name": page_info["name"],
                "type": "page",
                "token_type": "PageToken",
                "access_token": page_info["access_token"]
            })

    def post_comment(self, post_id: str, comment_text: str,
                     use_profile: Dict = None, attempt_num: int = 1) -> CommentResult:
        """Post a comment using available methods"""
        start_time = time.time()

        # Use main profile if not specified
        if not use_profile:
            use_profile = self.profiles[0]

        # Add variation to comment
        if attempt_num > 1:
            emojis = ['👍', '😊', '🙏', '🔥', '⭐']
            comment_text = f"{comment_text} {random.choice(emojis)}"

        result = CommentResult(
            success=False,
            session_id=self.session_id,
            profile_name=use_profile["name"],
            profile_type=use_profile["type"],
            attempt_num=attempt_num,
            method="",
            error="All methods failed"
        )

        # METHOD 1: Graph API with EAAG token
        if self.eaag_token and use_profile["type"] == "user":
            success, comment_id, error = self._graph_api_comment(
                post_id, comment_text, self.eaag_token)
            if success:
                result.success = True
                result.method = "GraphAPI"
                result.comment_id = comment_id
                result.elapsed = time.time() - start_time
                return result

        # METHOD 2: Graph API with page token
        if use_profile["type"] == "page" and "access_token" in use_profile:
            success, comment_id, error = self._graph_api_comment(
                post_id, comment_text, use_profile["access_token"])
            if success:
                result.success = True
                result.method = "GraphAPI-Page"
                result.comment_id = comment_id
                result.elapsed = time.time() - start_time
                return result

        # METHOD 3: Web GraphQL
        if self.fb_dtsg:
            success, comment_id, error = self._web_graphql_comment(
                post_id, comment_text, use_profile["id"])
            if success:
                result.success = True
                result.method = "WebGraphQL"
                result.comment_id = comment_id
                result.elapsed = time.time() - start_time
                return result

        result.elapsed = time.time() - start_time
        return result

    def _graph_api_comment(self, post_id: str, comment_text: str, token: str) -> Tuple[bool, str, str]:
        """Comment via Graph API"""
        try:
            encoded_comment = quote(comment_text)
            url = f"https://graph.facebook.com/{post_id}/comments?message={encoded_comment}&access_token={token}"

            response = self.session.post(url, timeout=5)
            data = response.json()

            if "id" in data:
                return True, data["id"], ""
            else:
                error = data.get("error", {}).get("message", "Unknown")
                return False, "", f"GraphAPI: {error}"
        except Exception as e:
            return False, "", f"GraphAPI Exception: {str(e)[:50]}"

    def _web_graphql_comment(self, post_id: str, comment_text: str, actor_id: str) -> Tuple[bool, str, str]:
        """Comment via Web GraphQL"""
        if not self.fb_dtsg:
            return False, "", "No web token"

        try:
            feedback_id = base64.b64encode(
                f"feedback:{post_id}".encode()).decode()

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
                'doc_id': '24615176934823390',
            }

            response = self.session.post(
                'https://www.facebook.com/api/graphql/',
                data=data,
                timeout=5
            )

            if response.status_code == 200 and '"comment_create"' in response.text:
                # Extract comment ID
                match = re.search(r'"comment_id":"([^"]+)"', response.text)
                comment_id = match.group(1) if match else "unknown"
                return True, comment_id, ""
            else:
                return False, "", f"HTTP:{response.status_code}"

        except Exception as e:
            return False, "", f"WebGraphQL: {str(e)[:50]}"


class ParallelFacebookBot:
    """Parallel Facebook comment bot using multiple sessions"""

    def __init__(self, cookie_strings: List[str]):
        """
        Initialize with multiple cookie strings

        Args:
            cookie_strings: List of cookie strings for different accounts
        """
        self.sessions = []
        self.session_lock = threading.Lock()
        self.results = []
        self.results_lock = threading.Lock()

        # Initialize sessions
        logger.info(f"🚀 Initializing {len(cookie_strings)} parallel sessions")
        for i, cookie_str in enumerate(cookie_strings):
            try:
                session = FacebookSession(f"Session_{i+1}", cookie_str)
                self.sessions.append(session)
                logger.info(
                    f"✅ Session {i+1}: {session.user_id} ({len(session.profiles)} profiles)")
            except Exception as e:
                logger.error(f"❌ Failed to init session {i+1}: {e}")

        if not self.sessions:
            raise ValueError("No valid sessions initialized")

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

    def _worker(self, session: FacebookSession, post_id: str, comment_text: str,
                profile_idx: int, total_comments: int, results_queue: Queue):
        """Worker function for posting comments"""
        profile = session.profiles[profile_idx % len(session.profiles)]

        result = session.post_comment(
            post_id=post_id,
            comment_text=comment_text,
            use_profile=profile,
            attempt_num=total_comments
        )

        results_queue.put(result)

    def rapid_comments_parallel(self, post_url: str, comment_text: str,
                                total_comments: int = 10, max_workers: int = 10) -> Dict:
        """
        Post comments in parallel using all available sessions and profiles

        Args:
            post_url: Facebook post URL
            comment_text: Comment text
            total_comments: Total comments to post
            max_workers: Maximum number of parallel workers

        Returns:
            Results dictionary
        """
        # Extract post ID
        post_id = self.extract_post_id(post_url)
        if not post_id:
            return {"error": "Invalid post URL"}

        logger.info("=" * 70)
        logger.info("⚡ PARALLEL RAPID COMMENT BOT")
        logger.info("=" * 70)
        logger.info(f"Sessions: {len(self.sessions)}")

        total_profiles = sum(len(s.profiles) for s in self.sessions)
        logger.info(f"Total profiles: {total_profiles}")
        logger.info(f"Target comments: {total_comments}")
        logger.info(f"Max parallel workers: {max_workers}")
        logger.info("=" * 70)

        # Prepare results queue
        results_queue = Queue()
        self.results = []

        # Calculate comments per session
        comments_per_session = total_comments // len(self.sessions)
        extra_comments = total_comments % len(self.sessions)

        start_time = time.time()

        # Use ThreadPoolExecutor for parallel execution
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            comment_counter = 1

            # Submit all comment tasks
            for session_idx, session in enumerate(self.sessions):
                session_comments = comments_per_session + \
                    (1 if session_idx < extra_comments else 0)

                for i in range(session_comments):
                    # Round-robin through profiles
                    profile_idx = (comment_counter - 1) % len(session.profiles)

                    future = executor.submit(
                        self._worker,
                        session,
                        post_id,
                        comment_text,
                        profile_idx,
                        comment_counter,
                        results_queue
                    )
                    futures.append(future)
                    comment_counter += 1

            # Collect results as they complete
            completed = 0
            successful = 0

            for future in as_completed(futures):
                try:
                    future.result()  # Just to raise any exceptions
                    completed += 1

                    # Get result from queue
                    if not results_queue.empty():
                        result = results_queue.get()
                        with self.results_lock:
                            self.results.append(result)

                        if result.success:
                            successful += 1
                            logger.info(
                                f"✅ Comment {result.attempt_num}: {result.profile_name} ({result.method}) - {result.elapsed:.2f}s")
                        else:
                            logger.info(
                                f"❌ Comment {result.attempt_num}: {result.profile_name} - {result.error}")

                    # Show progress
                    if completed % max_workers == 0 or completed == total_comments:
                        logger.info(
                            f"📊 Progress: {completed}/{total_comments} ({successful} successful)")

                except Exception as e:
                    logger.error(f"⚠️ Worker error: {e}")
                    completed += 1

        # Calculate statistics
        total_time = time.time() - start_time

        logger.info("\n" + "=" * 70)
        logger.info("📊 PARALLEL PERFORMANCE RESULTS")
        logger.info("=" * 70)
        logger.info(f"✅ Successful: {successful}/{total_comments}")
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

        # Session breakdown
        logger.info("\n📈 SESSION BREAKDOWN:")
        for session in self.sessions:
            session_results = [
                r for r in self.results if r.session_id == session.session_id]
            session_success = sum(1 for r in session_results if r.success)
            logger.info(
                f"  {session.session_id}: {session_success}/{len(session_results)} successful")

        # Profile breakdown
        logger.info("\n👥 PROFILE BREAKDOWN:")
        for session in self.sessions:
            for profile in session.profiles:
                profile_results = [
                    r for r in self.results if r.profile_name == profile["name"]]
                if profile_results:
                    success_count = sum(
                        1 for r in profile_results if r.success)
                    logger.info(
                        f"  {profile['name']}: {success_count}/{len(profile_results)} successful")

        logger.info("=" * 70)

        return {
            "status": "completed",
            "successful": successful,
            "total": total_comments,
            "speed": round(speed if successful > 0 else 0, 2),
            "total_time": round(total_time, 3),
            "sessions_used": len(self.sessions),
            "profiles_used": total_profiles,
            "parallel_workers": max_workers,
            "results": [{
                "session": r.session_id,
                "profile": r.profile_name,
                "type": r.profile_type,
                "attempt": r.attempt_num,
                "success": r.success,
                "method": r.method,
                "elapsed": round(r.elapsed, 3)
            } for r in self.results]
        }

# Test function


def test_parallel_bot():
    """Test the parallel bot with multiple sessions"""

    # Multiple cookie strings (replace with actual cookies)
    COOKIE_STRINGS = [
        "datr=SK8maRcMTTI5l5jYA2lNg9Vn; fr=10DTXgNJyOhjXXbVl.AWeWqJ_2gegQvWxTZiom95bjeXBPptBTlF70DcjGHpH3AM3dQ-A.BpRmyz..AAA.0.0.BpRmyz.AWdLi3KMi0AE8WbFy3tk_NlpQ1w; sb=SK8maQT5FcoNhX1ii3_svYfg; locale=en_US; wd=588x479; dpr=1.6800000667572021; ps_l=1; ps_n=1; c_user=100086111536900; xs=4%3AhEP3GPso2CzlRA%3A2%3A1766136688%3A-1%3A-1%3A%3AAczQc-ROIT3b9-QsJ-ly1BG_JahRSenkLut1oe9Jcw; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1766223040399%2C%22v%22%3A1%7D",
        "datr=wdAmaaHD99qka4MJumAg8qZZ; fr=1cWVgS3ej7r3NaUWg.AWd0cjvLnFjY4QoFgD17O6A2f8V4cjOri1Tlp2snyjU8yu5q7gQ.BpRmy2..AAA.0.0.BpRmy2.AWfqEmfEQuTnbPoYd_zLZ475hQg; sb=wdAmaXc2LA4x-8zm23MKb1bv; locale=en_IN; ps_l=1; ps_n=1; wd=588x479; dpr=1.6800000667572021; c_user=100005667075425; xs=43%3A0O5I6YRrUeLHvg%3A2%3A1766135152%3A-1%3A-1%3A%3AAcyAMox_lve16jzEAdsCb_ZcrtpwLm72mFN0sQumBA; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1766223042479%2C%22v%22%3A1%7D",
        "datr=GqwmaWOxLF_Uv-82ZWjF0eB6; fr=1s7Wi8byOKq6GuUar.AWd2YKoLPV4BF40OO77Am5hZJSryIVVjY3_ekNXfQuZ_KDqhgdM.BpRmy9..AAA.0.0.BpRmzI.AWfD17e6uN4qr7L7wqnD_FSxMZg; sb=GqwmaV_NuX4jWcP1nWNyzPKc; locale=en_GB; wd=1143x479; dpr=1.6800000667572021; ps_l=1; ps_n=1; c_user=100094329691764; xs=2%3AlGybrJRLGkeXtw%3A2%3A1766223031%3A-1%3A-1%3A%3AAcwigbCyQGtWhbpGI6oiaDxAVawef3FvWt-SS9AFHA"
    ]

    # Add dummy cookies for testing if only one provided
    if len(COOKIE_STRINGS) < 2:
        # Duplicate the first cookie (for testing only - use different accounts in production)
        COOKIE_STRINGS.append(COOKIE_STRINGS[0] + "_duplicate")

    POST_URL = "https://www.facebook.com/100068994467075/posts/534891072154037/"

    print("=" * 70)
    print("🚀 PARALLEL FACEBOOK COMMENT BOT TEST")
    print("=" * 70)

    try:
        # Create parallel bot
        bot = ParallelFacebookBot(COOKIE_STRINGS)

        print(f"\n✅ Bot initialized with {len(bot.sessions)} sessions")

        # Run rapid comments in parallel
        print("\n" + "=" * 70)
        print("🚀 STARTING PARALLEL COMMENTS")
        print("=" * 70)

        start_time = time.time()

        results = bot.rapid_comments_parallel(
            post_url=POST_URL,
            comment_text="Parallel bot test comment!",
            total_comments=10,  # Total comments to post
            max_workers=5      # Max parallel workers
        )

        total_time = time.time() - start_time

        # Summary
        print("\n🎯 FINAL RESULTS:")
        print(f"✅ Successful: {results['successful']}/{results['total']}")
        print(f"⚡ Speed: {results['speed']} comments/second")
        print(f"⏱️  Total time: {results['total_time']}s")
        print(f"🧵 Parallel workers: {results['parallel_workers']}")

        if results['speed'] >= 3:
            print("🏆 TARGET ACHIEVED! 3+ comments/second")
        else:
            print(f"⚠️ Below target: {results['speed']:.1f} comments/second")

        # Show some sample results
        print("\n📋 SAMPLE RESULTS:")
        for i, r in enumerate(results['results'][:5]):  # Show first 5
            status = "✅" if r['success'] else "❌"
            print(
                f"  {status} Comment {r['attempt']}: {r['profile']} ({r['method']}) - {r['elapsed']}s")

        if len(results['results']) > 5:
            print(f"  ... and {len(results['results']) - 5} more")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_parallel_bot()
