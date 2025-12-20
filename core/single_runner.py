import re
import sys
import json
import time
import threading
import random
from typing import Dict
from facebook_mobile_manager import FacebookMobileManager, MobileFacebookThread


class RunSingleOptimized(threading.Thread):
    """Optimized single account runner using mobile API"""

    def __init__(self, cookie, post_link, comment, comment_per_acc, options, result_container):
        super().__init__()
        self.cookie = cookie
        self.post_link = post_link
        self.comment = comment
        self.comment_per_acc = comment_per_acc
        self.options = options
        self.result_container = result_container

        # Extract cookie string and user agent
        self.cookie_str = list(cookie.keys())[0]
        self.user_agent = cookie.get(self.cookie_str)[0]

        # Performance settings
        self.delay_ms = 100  # 0.1 seconds between comments
        self.max_retries = 2

        print(f"🚀 Initialized optimized runner for post: {post_link}")

    def run(self):
        """Main execution method"""
        try:
            # Create mobile manager
            manager = FacebookMobileManager(
                cookie_string=self.cookie_str,
                user_agent=self.user_agent,
                result_container=self.result_container
            )

            # Check if session initialized successfully
            if not manager.fb_dtsg:
                print(f"❌ Account locked or invalid: {manager.user_id}")
                self.result_container['locked'].append(self.cookie_str)
                return

            # Extract user's pages if needed
            if self.options.get('from_page', False):
                # You can add page extraction logic here
                # For now, we'll just use the main user
                pass

            # Determine profiles to post from
            profiles_to_post = []

            if self.options.get('from_user', True):
                profiles_to_post.append({
                    'id': manager.user_id,
                    'name': 'Main User',
                    'is_page': False
                })

            # If you have pages, add them here
            # profiles_to_post.extend(self.extract_pages(manager))

            # Post comments
            total_comments = 0
            success_count = 0

            for profile in profiles_to_post:
                print(f"\n📱 Posting from {profile['name']}...")

                # Get post info once per profile
                post_info = manager.extract_post_info(self.post_link)
                if not post_info:
                    print(
                        f"❌ Failed to extract post info for {profile['name']}")
                    continue

                for i in range(self.comment_per_acc):
                    total_comments += 1

                    # Add variation to avoid spam detection
                    current_comment = self.comment
                    if i > 0:
                        emojis = ['👍', '😊', '🙏', '🔥', '⭐']
                        current_comment = f"{self.comment} {random.choice(emojis)}"

                    print(f"  → Comment {i+1}/{self.comment_per_acc}")

                    # Retry logic
                    for retry in range(self.max_retries):
                        success, result = manager.post_comment_mobile(
                            post_info=post_info,
                            comment_text=current_comment,
                            profile_id=profile['id'],
                            is_page=profile['is_page']
                        )

                        if success:
                            success_count += 1
                            print(f"    ✅ Success! ID: {result[:20]}...")

                            # Add to results
                            self.result_container['success'].append({
                                'profile': profile['name'],
                                'profile_id': profile['id'],
                                'comment_id': result,
                                'timestamp': time.time()
                            })

                            # Minimal delay between comments
                            if i < self.comment_per_acc - 1:
                                time.sleep(self.delay_ms / 1000.0)

                            break  # Success, no need to retry

                        else:
                            print(f"    ⚠️ Attempt {retry+1} failed: {result}")

                            if retry < self.max_retries - 1:
                                # Exponential backoff
                                wait_time = (2 ** retry) * 0.5
                                print(f"    ⏳ Retrying in {wait_time}s...")
                                time.sleep(wait_time)
                            else:
                                print(
                                    f"    ❌ Final failure for {profile['name']}")
                                self.result_container['failure'].append({
                                    'profile': profile['name'],
                                    'error': result,
                                    'timestamp': time.time()
                                })
                                break  # Move to next profile

            print(
                f"\n📊 Runner completed: {success_count}/{total_comments} successful")

        except Exception as e:
            print(f"❌ Runner error: {e}")
            import traceback
            traceback.print_exc()

            self.result_container['failure'].append({
                'error': str(e),
                'timestamp': time.time()
            })

    def extract_pages(self, manager):
        """Extract user's pages (placeholder - implement your logic)"""
        # This is where you'd add your page extraction logic
        # For now, return empty list
        return []


# Legacy compatibility wrapper
class FacebookCommentBot:
    """Legacy compatibility wrapper"""

    def __init__(self, cookie_string, user_agent, ua_parts, post_link, result_container, i_user=None):
        self.cookie_str = cookie_string
        self.user_agent = user_agent
        self.post_link = post_link
        self.result_container = result_container
        self.i_user = i_user

        # Create mobile manager
        self.manager = FacebookMobileManager(
            cookie_string=cookie_string,
            user_agent=user_agent,
            result_container=result_container
        )

    def execute_comment(self, user, is_main_user, post_link, comment, total_comments_to_post):
        """Execute comments using mobile API"""

        if not self.manager.fb_dtsg:
            return False, "Session not initialized", {}

        # Get post info
        post_info = self.manager.extract_post_info(post_link)
        if not post_info:
            return False, "Could not extract post info", {}

        results = []
        success_count = 0

        for i in range(total_comments_to_post):
            # Add variation
            current_comment = comment
            if i > 0:
                emojis = ['👍', '😊', '🙏', '🔥', '⭐']
                current_comment = f"{comment} {random.choice(emojis)}"

            # Post comment
            success, result = self.manager.post_comment_mobile(
                post_info=post_info,
                comment_text=current_comment,
                profile_id=self.i_user if self.i_user else user,
                is_page=not is_main_user
            )

            if success:
                success_count += 1
                results.append({
                    'success': True,
                    'comment_id': result,
                    'profile': 'Page' if not is_main_user else 'User'
                })

                # Add to container
                self.result_container['success'].append({
                    'profile_id': self.i_user if self.i_user else user,
                    'comment_id': result,
                    'timestamp': time.time()
                })

                # Minimal delay
                if i < total_comments_to_post - 1:
                    time.sleep(0.1)  # 100ms
            else:
                results.append({
                    'success': False,
                    'error': result,
                    'profile': 'Page' if not is_main_user else 'User'
                })

                self.result_container['failure'].append({
                    'profile_id': self.i_user if self.i_user else user,
                    'error': result,
                    'timestamp': time.time()
                })
                break

        return success_count > 0, f"{success_count}/{total_comments_to_post} successful", {'results': results}


# Example usage
if __name__ == "__main__":
    # Test configuration
    COOKIE_STRING = "c_user=100027467101901; xs=23%3AEc-6Y5UZ4xLX0Q%3A2%3A1766167217%3A-1%3A-1%3A%3AAcyuC06JDE7T2dDtsw3jXIRRfa5P4fHbCrnHmZEXiw"
    MOBILE_USER_AGENT = "[FBAN/FB4A;FBAV/434.0.0.35.114;FBBV/468570802;FBDM/{density=3.0,width=1080,height=2340};FBLC/en_US;FBRV/0;FBCR/AT&T;FBMF/samsung;FBBD/samsung;FBPN/com.facebook.katana;FBDV/SM-S911B;FBSV/13;FBOP/1;FBCA/arm64-v8a:]"

    # Test post
    POST_URL = "https://www.facebook.com/100068994467075/posts/534891072154037/"

    # Create result container
    result_container = {
        'success': [],
        'failure': [],
        'locked': []
    }

    # Test the optimized runner
    print("🧪 Testing optimized mobile comment bot...")

    # Method 1: Direct manager
    manager = FacebookMobileManager(
        cookie_string=COOKIE_STRING,
        user_agent=MOBILE_USER_AGENT,
        result_container=result_container
    )

    results = manager.post_comments_fast(
        post_url=POST_URL,
        comment_text="Test comment from optimized bot!",
        comments_per_profile=2,
        delay_ms=100  # 0.1 second delay
    )

    print(json.dumps(results, indent=2))

    # Method 2: Threaded
    print("\n🧪 Testing threaded version...")

    thread = MobileFacebookThread(
        cookie_string=COOKIE_STRING,
        user_agent=MOBILE_USER_AGENT,
        post_link=POST_URL,
        comment="Thread test comment",
        comment_per_acc=2,
        result_container=result_container
    )

    thread.start()
    thread.join()

    if thread.results:
        print(json.dumps(thread.results, indent=2))
