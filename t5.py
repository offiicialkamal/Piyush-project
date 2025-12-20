#!/usr/bin/env python3
"""
ULTIMATE FACEBOOK COMMENT BOT - Pre-Login & Fast Comment
Login first, then lightning-fast commenting on command
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
import sys

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

        # Status
        self.initialized = False
        self.login_time = None

    def _parse_cookies(self, cookie_string: str) -> Dict:
        """Parse cookie string"""
        cookies = {}
        for item in cookie_string.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key] = value
        return cookies

    def initialize(self) -> bool:
        """Initialize session - login and get tokens"""
        try:
            logger.info(f"🔐 Logging in {self.session_id}...")

            # EAAG Token
            url = "https://business.facebook.com/business_locations"
            response = self.session.get(url, timeout=10)
            match = re.search(r'(\["EAAG\w+)', response.text)
            if match:
                self.eaag_token = match.group(1).replace('["', '')
                logger.info(f"  ✅ EAAG token obtained")

            # Web token
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
                    logger.info(f"  ✅ Web token obtained")
                    break

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
                        logger.info(f"  ✅ {len(self.page_tokens)} pages found")
                except Exception as e:
                    logger.info(f"  ⚠️ No pages: {e}")

            # Prepare profiles
            self._prepare_profiles()

            self.initialized = True
            self.login_time = time.time()

            logger.info(
                f"✅ {self.session_id} ready ({len(self.profiles)} profiles)")
            return True

        except Exception as e:
            logger.error(f"❌ {self.session_id} failed: {e}")
            return False

    def _prepare_profiles(self):
        """Prepare list of available profiles"""
        # Add main user
        self.profiles.append({
            "id": self.user_id,
            "name": f"User_{self.user_id[:6]}",
            "type": "user",
            "token_type": "EAAG" if self.eaag_token else "Web",
            "access_token": self.eaag_token if self.eaag_token else None
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

        # METHOD 1: Graph API (preferred - fastest)
        if use_profile.get("access_token"):
            success, comment_id, error = self._graph_api_comment(
                post_id, comment_text, use_profile["access_token"])
            if success:
                result.success = True
                result.method = "GraphAPI"
                result.comment_id = comment_id
                result.elapsed = time.time() - start_time
                return result

        # METHOD 2: Web GraphQL (fallback)
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

            response = self.session.post(
                url, timeout=3)  # Short timeout for speed
            data = response.json()

            if "id" in data:
                return True, data["id"], ""
            else:
                error = data.get("error", {}).get("message", "Unknown")
                return False, "", f"GraphAPI: {error}"
        except Exception as e:
            return False, "", f"GraphAPI: {str(e)[:30]}"

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
                timeout=3  # Short timeout
            )

            if response.status_code == 200 and '"comment_create"' in response.text:
                # Extract comment ID
                match = re.search(r'"comment_id":"([^"]+)"', response.text)
                comment_id = match.group(1) if match else "unknown"
                return True, comment_id, ""
            else:
                return False, "", f"HTTP:{response.status_code}"

        except Exception as e:
            return False, "", f"WebGraphQL: {str(e)[:30]}"


class LightningCommentBot:
    """Lightning-fast comment bot with pre-login"""

    def __init__(self, cookie_strings: List[str]):
        """
        Initialize with multiple cookie strings

        Args:
            cookie_strings: List of cookie strings for different accounts
        """
        self.sessions = []
        self.ready_sessions = []
        self.total_profiles = 0

        print("\n" + "="*70)
        print("🚀 LIGHTNING COMMENT BOT - PRE-LOGIN PHASE")
        print("="*70)

        # Initialize all sessions
        self._initialize_sessions(cookie_strings)

        if not self.ready_sessions:
            raise ValueError("No valid sessions initialized")

        print("="*70)
        print(
            f"✅ PRE-LOGIN COMPLETE: {len(self.ready_sessions)} sessions, {self.total_profiles} profiles")
        print("="*70)

    def _initialize_sessions(self, cookie_strings: List[str]):
        """Initialize all sessions in parallel"""
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []

            for i, cookie_str in enumerate(cookie_strings):
                session_id = f"Session_{i+1}"
                future = executor.submit(
                    self._create_session, session_id, cookie_str)
                futures.append(future)

            # Wait for all sessions to initialize
            for future in concurrent.futures.as_completed(futures):
                try:
                    session = future.result()
                    if session:
                        self.ready_sessions.append(session)
                        self.total_profiles += len(session.profiles)
                except Exception as e:
                    logger.error(f"Session failed: {e}")

    def _create_session(self, session_id: str, cookie_str: str) -> Optional[FacebookSession]:
        """Create and initialize a session"""
        try:
            session = FacebookSession(session_id, cookie_str)
            if session.initialize():
                return session
        except Exception as e:
            logger.error(f"{session_id} creation failed: {e}")
        return None

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

    def wait_for_command(self):
        """Wait for user to start commenting"""
        print("\n" + "="*70)
        print("⚡ READY FOR LIGHTNING COMMENTING")
        print("="*70)
        print(
            f"📊 Available: {len(self.ready_sessions)} sessions, {self.total_profiles} profiles")
        print(f"⚡ Each session ready with tokens pre-loaded")
        print(f"🚀 Comments will fire instantly on command")
        print("="*70)

        while True:
            cmd = input(
                "\n🔥 Enter 'Y' to start commenting (or 'Q' to quit): ").strip().upper()

            if cmd == 'Q':
                print("👋 Exiting...")
                sys.exit(0)
            elif cmd == 'Y':
                return True
            else:
                print("⚠️ Press 'Y' to start or 'Q' to quit")

    def rapid_comments_lightning(self, post_url: str, comment_text: str,
                                 total_comments: int = 10, max_workers: int = 10) -> Dict:
        """
        Lightning-fast parallel commenting

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

        print("\n" + "="*70)
        print("⚡ LIGHTNING COMMENTING STARTED")
        print("="*70)
        print(f"🎯 Target: {total_comments} comments")
        print(f"🧵 Parallel workers: {max_workers}")
        print("="*70)

        # Prepare results
        results_queue = Queue()
        all_results = []
        results_lock = threading.Lock()

        start_time = time.time()

        # Use ThreadPoolExecutor for maximum parallelism
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            comment_counter = 1

            # Distribute comments across sessions and profiles
            comments_per_session = total_comments // len(self.ready_sessions)
            extra_comments = total_comments % len(self.ready_sessions)

            for session_idx, session in enumerate(self.ready_sessions):
                session_comments = comments_per_session + \
                    (1 if session_idx < extra_comments else 0)

                for i in range(session_comments):
                    # Round-robin through profiles
                    profile_idx = (comment_counter - 1) % len(session.profiles)
                    profile = session.profiles[profile_idx]

                    future = executor.submit(
                        self._comment_worker,
                        session,
                        post_id,
                        comment_text,
                        profile,
                        comment_counter,
                        results_queue
                    )
                    futures.append(future)
                    comment_counter += 1

            # Collect results
            completed = 0
            successful = 0

            # Show initial progress
            print(f"\n🚀 Launching {len(futures)} parallel comments...")

            for future in as_completed(futures):
                try:
                    future.result()  # Just to raise any exceptions
                    completed += 1

                    # Get result from queue
                    if not results_queue.empty():
                        result = results_queue.get()
                        with results_lock:
                            all_results.append(result)

                        if result.success:
                            successful += 1
                            # Show success quickly
                            print(
                                f"✅ {result.profile_name}: {result.method} ({result.elapsed:.2f}s)")
                        else:
                            # Show failures briefly
                            print(
                                f"❌ {result.profile_name}: {result.error[:20]}")

                    # Show progress every few comments
                    if completed % max_workers == 0 or completed == total_comments:
                        print(
                            f"📊 {completed}/{total_comments} ({successful} ✅)")

                except Exception as e:
                    print(f"⚠️ Error: {e}")
                    completed += 1

        # Calculate statistics
        total_time = time.time() - start_time

        print("\n" + "="*70)
        print("📊 LIGHTNING RESULTS")
        print("="*70)
        print(f"✅ Successful: {successful}/{total_comments}")
        print(f"⏱️  Total time: {total_time:.3f}s")

        if successful > 0:
            speed = successful / total_time
            print(f"⚡ Speed: {speed:.2f} comments/second")

            if speed >= 3:
                print(f"🏆 TARGET ACHIEVED: {speed:.1f} ≥ 3 comments/second!")
            else:
                print(f"⚠️ Below target: {speed:.1f} < 3 comments/second")

        # Session breakdown
        print("\n📈 SESSION PERFORMANCE:")
        for session in self.ready_sessions:
            session_results = [
                r for r in all_results if r.session_id == session.session_id]
            if session_results:
                session_success = sum(1 for r in session_results if r.success)
                avg_time = sum(r.elapsed for r in session_results) / \
                    len(session_results)
                print(
                    f"  {session.session_id}: {session_success}/{len(session_results)} ({avg_time:.2f}s avg)")

        print("="*70)

        return {
            "status": "completed",
            "successful": successful,
            "total": total_comments,
            "speed": round(speed if successful > 0 else 0, 2),
            "total_time": round(total_time, 3),
            "sessions_used": len(self.ready_sessions),
            "profiles_used": self.total_profiles,
            "parallel_workers": max_workers,
            "results": [{
                "session": r.session_id,
                "profile": r.profile_name,
                "type": r.profile_type,
                "attempt": r.attempt_num,
                "success": r.success,
                "method": r.method,
                "elapsed": round(r.elapsed, 3)
            } for r in all_results]
        }

    def _comment_worker(self, session: FacebookSession, post_id: str,
                        comment_text: str, profile: Dict, attempt_num: int,
                        results_queue: Queue):
        """Worker function for posting comments"""
        result = session.post_comment(
            post_id=post_id,
            comment_text=comment_text,
            use_profile=profile,
            attempt_num=attempt_num
        )
        results_queue.put(result)


def main():
    """Main function with interactive CLI"""

    # Your cookie strings (add more for more accounts)
    # COOKIE_STRINGS = [
    #     "datr=SK8maRcMTTI5l5jYA2lNg9Vn; fr=10DTXgNJyOhjXXbVl.AWeWqJ_2gegQvWxTZiom95bjeXBPptBTlF70DcjGHpH3AM3dQ-A.BpRmyz..AAA.0.0.BpRmyz.AWdLi3KMi0AE8WbFy3tk_NlpQ1w; sb=SK8maQT5FcoNhX1ii3_svYfg; locale=en_US; wd=588x479; dpr=1.6800000667572021; ps_l=1; ps_n=1; c_user=100086111536900; xs=4%3AhEP3GPso2CzlRA%3A2%3A1766136688%3A-1%3A-1%3A%3AAczQc-ROIT3b9-QsJ-ly1BG_JahRSenkLut1oe9Jcw; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1766223040399%2C%22v%22%3A1%7D",
    #     "datr=wdAmaaHD99qka4MJumAg8qZZ; fr=1cWVgS3ej7r3NaUWg.AWd0cjvLnFjY4QoFgD17O6A2f8V4cjOri1Tlp2snyjU8yu5q7gQ.BpRmy2..AAA.0.0.BpRmy2.AWfqEmfEQuTnbPoYd_zLZ475hQg; sb=wdAmaXc2LA4x-8zm23MKb1bv; locale=en_IN; ps_l=1; ps_n=1; wd=588x479; dpr=1.6800000667572021; c_user=100005667075425; xs=43%3A0O5I6YRrUeLHvg%3A2%3A1766135152%3A-1%3A-1%3A%3AAcyAMox_lve16jzEAdsCb_ZcrtpwLm72mFN0sQumBA; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1766223042479%2C%22v%22%3A1%7D",
    #     "datr=GqwmaWOxLF_Uv-82ZWjF0eB6; fr=1s7Wi8byOKq6GuUar.AWd2YKoLPV4BF40OO77Am5hZJSryIVVjY3_ekNXfQuZ_KDqhgdM.BpRmy9..AAA.0.0.BpRmzI.AWfD17e6uN4qr7L7wqnD_FSxMZg; sb=GqwmaV_NuX4jWcP1nWNyzPKc; locale=en_GB; wd=1143x479; dpr=1.6800000667572021; ps_l=1; ps_n=1; c_user=100094329691764; xs=2%3AlGybrJRLGkeXtw%3A2%3A1766223031%3A-1%3A-1%3A%3AAcwigbCyQGtWhbpGI6oiaDxAVawef3FvWt-SS9AFHA"
    # ]

    COOKIE_STRINGS = [
        "datr=zxQfaSknsVyoOjNgfRAbNOsP; fr=1Tzvo8pRXxHvn3cqW.AWenkVDK3YMBNGh2H6Mjh97LFE7hwVVmP0sdgFLgImf2RWpJYXM.BpRnvj..AAA.0.0.BpRnvj.AWf5X9Kp1k3nGUPLxjNPgTyDGG4; sb=zxQfaV8env0kkpYzJWg9YdWU; ps_l=1; ps_n=1; wd=588x479; dpr=1.6800000667572021; c_user=100070270166168; xs=13%3AEyOQ58iNyJ0-lg%3A2%3A1766226912%3A-1%3A-1%3A%3AAcxVfiYLYtwIxVsOlCwQXn-ri9Xmgnp-2CpZ4OiXuA; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1766226931869%2C%22v%22%3A1%7D",
        "datr=rl0kaQTyS3JBddEItXeXJH7V; fr=1ev5DVU47C0jk3iL6.AWerSwrcmsjAqd_oRJ8SsOoeCbITw56yuehGt8J-YcVoCjCL4Ew.BpRnvh..AAA.0.0.BpRnvh.AWcuu3GVOLJkNoSj3jf0lX_HoLk; sb=hwUfaWNivCnesLvoBoizObSp; ps_l=1; ps_n=1; wd=588x479; dpr=1.6800000667572021; c_user=100075642400293; xs=24%3AeguKQDp7EejI5Q%3A2%3A1766076229%3A-1%3A-1%3A%3AAcxilzY_q_Drln0KTYghIYmyEwesTE5P-K-WWnMJOg; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1766226926765%2C%22v%22%3A1%7D",
        "datr=h1EsaXrGo7AhSbiwkY0rRWvg; fr=1IrF92WmRIxmp8HxD.AWcHDd1fCPztTfg_Nxg7gHYXNICNmt02x1ElyXwWdQ2uZw5Ztfs.BpRnw9..AAA.0.0.BpRnxC.AWcM4bdmiQqdLIShs5zmgmAb9cg; sb=2SgfaXcag0lZuNFZVCICjDTe; ps_l=1; ps_n=1; wd=588x479; dpr=1.6800000667572021; c_user=100054952179705; xs=36%3AUEhw7CcOa4IP5w%3A2%3A1766227000%3A-1%3A-1%3A%3AAcwE7WrMIwk8jyWCqvt21yKzSYbd9nC6YLAlCidpDg; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1766227028155%2C%22v%22%3A1%7D",
        "datr=DocxaWrzb39bBeo7s2I8njsz; fr=1iGFAfzgUheqYx1uw.AWchkzdXp1kCx83savoqslCvBZa4TFhKurU4d0TqtSiCra0naOw.BpRnvi..AAA.0.0.BpRnvi.AWcjZJlKbn6pKF1n4YFOL6G-LAQ; sb=0iUfaaP-2sqMi-j3opUCF4Nb; ps_l=1; ps_n=1; wd=588x479; dpr=1.6800000667572021; c_user=100056507890889; xs=45%3AX-SC_-7vqtFnfg%3A2%3A1766076403%3A-1%3A-1%3A%3AAcwgChsqrLytUYBaN0Tmpz1X7DKGAc2ezIJdK5eAog; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1766226926476%2C%22v%22%3A1%7D",
        "datr=DSEfaaaJjbEJrcgF3e0dHpG0; fr=1dfAvwH4RdFRkmmJc.AWdQeRgHJ0h6HdD1c70j69c00oyjGTHqSSi1WVPOrBsx3VVrTN0.BpRnvh..AAA.0.0.BpRnvh.AWeJzE6GwT9lG6n46g2QZDkX2sU; sb=DSEfaYPFaC7kM5CKaCg3W73V; ps_l=1; ps_n=1; wd=588x479; dpr=1.6800000667572021; c_user=100056999746122; xs=27%3A-K7Has_R4iJv_g%3A2%3A1766076431%3A-1%3A-1%3A%3AAcw0rzx0C8nPSZiEciVEVQf51YTGkoVIjMVWIeq4ZQ; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1766226925658%2C%22v%22%3A1%7D",
        "datr=wF0kaXnpJzXNk42XtqtSX-Xg; fr=1689XfMuV6bWAAFrM.AWd5C0A6n8-QBk0hCc33uQJIcPqzAqKhSXvLp1L3NYDgbsYupbw.BpRnyz..AAA.0.0.BpRnyz.AWdO-usg8dd7ITQQsoc7w10DfY0; sb=mxwfaYh8e_c0snIoXjcnEVOP; ps_l=1; ps_n=1; wd=588x479; dpr=1.6800000667572021; c_user=100058181426826; xs=32%3Ac09t-0y4UJ7nWg%3A2%3A1766227119%3A-1%3A-1%3A%3AAcxlnLqKy_e1jCmsi_fdvLlLViYvYHT58ldyJ4XYwQ; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1766227139108%2C%22v%22%3A1%7D",
        "datr=nhgfaUbJvjR2IWY_Eu_NQlsp; fr=1OvTjtggBrMrP3XJ8.AWcljCreaB02T1chinEVcGHZYLRVBi7lic795U1aiqdCy6_x-kQ.BpRny3..AAA.0.0.BpRny9.AWfO2jqsen9cmdvkfJry36mCTqQ; sb=nhgfaVnvzv60w13I3_V-RPu0; ps_l=1; ps_n=1; wd=588x479; dpr=1.6800000667572021; c_user=100060533590391; xs=14%3A2cIecquEBg7IRg%3A2%3A1766227121%3A-1%3A-1%3A%3AAcy4xnZZaVnyzgBvNKAdelSy4D-Mb3MXjCa_JfnvZw; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1766227150916%2C%22v%22%3A1%7D",
        "datr=BsclaeDwgdEAXnEgJDXvWtoe; fr=1EflleCZoh2XGPtbV.AWf9Q2J0VcvXQea8HcA4_25y9XlCnTqtda9jw7v06245JQY659M.BpRn40..AAA.0.0.BpRn46.AWd1FD6bNdmb0iZY6RHtnGn_pDU; ps_l=1; ps_n=1; sb=BsclabxMPm9CVc7mhsGuLncT; wd=588x479; dpr=1.6800000667572021; c_user=100078212000631; xs=21%3AG3QwMN4pFBXTpQ%3A2%3A1766227501%3A-1%3A-1%3A%3AAcyyBbVMLaPBhTQ_z_IKSl4J8y4_HuB4zrY-gdBvKA; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1766227537454%2C%22v%22%3A1%7D",
        "datr=tMclaeOwspfNs6HzLISI-s9y; fr=1Im45tfrvN6LssoGT.AWdFObrjtR656tFPfIHz3-4hDjk8uj07RaDaHhaVJ05r-2Jc_No.BpRn4v..AAA.0.0.BpRn4v.AWeSF-tifVorL7FbTAndExHwJZk; sb=tMclaZZTwXLx62_BKiHz6X90; wd=588x479; dpr=1.6800000667572021; ps_l=1; ps_n=1; c_user=100009859368702; xs=43%3AAjkDLrFSBteErQ%3A2%3A1766227499%3A-1%3A-1%3A%3AAczvaw01a-_4MMKX2xFYnqLaBJ0iFtwgkEZoweDbQw; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1766227524909%2C%22v%22%3A1%7D",
        "datr=KM8laXcUrPkdpgXvSarjE2sK; fr=1fY1OqUTswYHhBM5B.AWfi95jak9REaETfmd22mz9ZJhbWEzr4PYm0M_S05C7UTjLgwkQ.BpRn4t..AAA.0.0.BpRn4_.AWczETPEGlk45SSRS3tW8WkBT9E; sb=KM8laQmbmxDnh3uEbA0x6Wdr; ps_l=1; ps_n=1; wd=588x479; dpr=1.6800000667572021; c_user=100070292709972; xs=48%3AuxhTAGSjhvv7Cw%3A2%3A1766227494%3A-1%3A-1%3A%3AAcyEibjHYlDAinIVMzEzHpDKpRJaWQ79b-KR2dxq5w",
        "datr=srsxaSSBP6uNC1C6lmF1DotN; fr=1tEygJaC5i6fk44mU.AWeOOFjQFjEvE_u6VtM2QcWFfZDxvne-v7u8KpYAFs1SbqeZQsI.BpRn7y..AAA.0.0.BpRn73.AWeJ_Krybcthov2VTcZ_6eQJU7w; sb=srsxacluoPxqlKN7d29eKcqQ; wd=588x479; dpr=1.6800000667572021; ps_l=1; ps_n=1; ar_debug=1; c_user=100086304251378; xs=43%3A6Rbm-l7APY1JnQ%3A2%3A1766227693%3A-1%3A-1%3A%3AAcw5ZdCGCfEFPEykqhCZ6kVdgiLiBJKjvpRkURMlDA; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1766227725244%2C%22v%22%3A1%7D",
        "datr=T7sxaXAH9WyEahTblLxuq_na; fr=1xNCiV38nZbaZwBOz.AWdRsoJHHQmdwwkUBIYR8Ax75KjqhOgVS-896vLxDlEPxLyMRTU.BpRn6g..AAA.0.0.BpRn6g.AWc10ISiiEA170oPzNw9coVzWZA; sb=T7sxaXOmXUUhSyvnLBqiITH_; ps_l=1; ps_n=1; wd=588x479; dpr=1.6800000667572021; c_user=100052293248905; xs=41%3ADC2jCSr3UMx9aw%3A2%3A1766076549%3A-1%3A-1%3A%3AAcxC83pz0Jao348-jhS6EJ0rBhEvBOuTuf-DeYYXnw; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1766227628692%2C%22v%22%3A1%7D",
        "datr=KY8waSiJnbB2MYm4XTxWhv7k; fr=1No0mtiQFKQWKrBX8.AWdsC5hG1tXRB0gJEN4fLan4zuLEOf81KZyypiQ5gNGM2DodriE.BpRn6d..AAA.0.0.BpRn6d.AWdQA7ghxiYVjYyxRSjQMKfHork; sb=KY8wacKV-GEdbpSb-Aeh2ru0; ps_l=1; ps_n=1; wd=588x479; dpr=1.6800000667572021; c_user=100082121894581; xs=40%3ADcEMVEjTBwCIMA%3A2%3A1766076564%3A-1%3A-1%3A%3AAcwNsV9zkzdnqQb-BV4KGAep9ohC1UT4u0RxHmRetg; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1766227628845%2C%22v%22%3A1%7D",
        "datr=eYowaVOEtn8QmBgu0V0Ak390; fr=1vCGnzkdbPtD8zcvv.AWewe4LS50RsjIuqkUv1xGZ9WzkBC_NipmFnYgHUQdTqLtb81_E.BpRn8p..AAA.0.0.BpRn8p.AWeax4bEqt9oMUgrnDfB4Tyf8lo; sb=eYowaVvM6l0FRwH3SvaciMwq; wd=588x479; dpr=1.6800000667572021; c_user=100086089861911; xs=33%3AXSGVWqoHY99svA%3A2%3A1766227748%3A-1%3A-1%3A%3AAcyyw5Xy6dXQkDFR5n9mDMQEqwcO-lKFCGPo_HlYzw; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1766227768753%2C%22v%22%3A1%7D; ps_l=1; ps_n=1"
    ]

    # Test URL
    # "https://www.facebook.com/100068994467075/posts/534891072154037/"
    TEST_POST_URL = "https://www.facebook.com/61584256683639/posts/122108015655141889/"

    print("\n" + "="*70)
    print("⚡ ULTIMATE FACEBOOK COMMENT BOT")
    print("="*70)
    print("🔥 Features:")
    print("  • Pre-login all sessions")
    print("  • Lightning-fast parallel commenting")
    print("  • Auto-fallback methods")
    print("  • Multi-account support")
    print("="*70)

    try:
        # STEP 1: Initialize and pre-login all sessions
        print("\n📥 Initializing bot...")
        bot = LightningCommentBot(COOKIE_STRINGS)

        # STEP 2: Get user input
        print("\n📝 Please provide comment details:")
        post_url = input("Enter post URL (press Enter for default): ").strip()
        if not post_url:
            post_url = TEST_POST_URL
            print(f"Using default: {post_url}")

        comment_text = input("Enter comment text: ").strip()
        if not comment_text:
            comment_text = "Lightning fast comment! ⚡"
            print(f"Using default: {comment_text}")

        try:
            total_comments = int(
                input("Number of comments to post (default: 10): ").strip() or "10")
        except:
            total_comments = 10
            print(f"Using default: {total_comments}")

        try:
            max_workers = int(
                input("Parallel workers (default: 8): ").strip() or "8")
        except:
            max_workers = 8
            print(f"Using default: {max_workers}")

        # STEP 3: Wait for start command
        print("\n" + "="*70)
        print("🎯 READY TO FIRE")
        print("="*70)
        print(f"Post: {post_url}")
        print(f"Comment: {comment_text}")
        print(f"Target: {total_comments} comments")
        print(f"Parallelism: {max_workers} workers")
        print("="*70)

        if not bot.wait_for_command():
            return

        # STEP 4: Lightning-fast commenting
        print("\n🔥 FIRING COMMENTS IN 3...")
        time.sleep(1)
        print("🔥 2...")
        time.sleep(1)
        print("🔥 1...")
        time.sleep(1)
        print("🔥 GO! ⚡\n")

        # Start timing
        overall_start = time.time()

        # Run the lightning commenter
        results = bot.rapid_comments_lightning(
            post_url=post_url,
            comment_text=comment_text,
            total_comments=total_comments,
            max_workers=max_workers
        )

        overall_time = time.time() - overall_start

        # Final summary
        print("\n" + "="*70)
        print("🎯 MISSION COMPLETE")
        print("="*70)
        print(f"✅ Successful: {results['successful']}/{results['total']}")
        print(f"⚡ Speed: {results['speed']} comments/second")
        print(f"⏱️  Commenting time: {results['total_time']}s")
        print(f"⏱️  Overall time: {overall_time:.2f}s")
        print(f"🧵 Workers used: {results['parallel_workers']}")

        if results['speed'] >= 3:
            print("🏆 TARGET ACHIEVED! Lightning speed!")
        else:
            print(f"⚠️ Below target speed")

        print("="*70)

        # Ask if user wants to continue
        while True:
            again = input("\nRun again? (Y/N): ").strip().upper()
            if again == 'Y':
                # Keep same sessions, just run again
                if not bot.wait_for_command():
                    break

                print("\n🔥 RE-FIRING COMMENTS...\n")
                results = bot.rapid_comments_lightning(
                    post_url=post_url,
                    comment_text=comment_text,
                    total_comments=total_comments,
                    max_workers=max_workers
                )

                print("\n" + "="*70)
                print(
                    f"✅ Successful: {results['successful']}/{results['total']}")
                print(f"⚡ Speed: {results['speed']} comments/second")
                print("="*70)

            elif again == 'N':
                print("\n👋 Session ended. Goodbye!")
                break

    except KeyboardInterrupt:
        print("\n\n⚠️ Stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
