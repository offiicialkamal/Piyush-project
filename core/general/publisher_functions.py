import requests
import json
import re
import time
import uuid
import base64
from typing import Dict, Optional, Tuple


class FacebookCommentBot:
    def __init__(self, cookie_string, user_agent, ua_parts, post_link, i_user=None):
        self.user_agent = user_agent
        self.session = requests.Session()
        self.cookies = cookie_string
        self.session.cookies.update(self.cookies)
        self.ua_parts = ua_parts
        self.post_link = post_link
        # User ID from cookies
        self.user_id = self.cookies.get('c_user', '')
        self.i_user = i_user

        # Base headers
        self.base_headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,mr;q=0.6',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }

        # Volatile parameters storage
        self.volatile_params = {}
        self.request_counter = 0

        # print(f"✅ Bot initialized for user: {self.user_id}")


    def _extract_from_html(self, html: str, patterns: list) -> Optional[str]:
        """Extract value from HTML using multiple regex patterns."""
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                return match.group(1)
        return None



    def fetch_post_page(self, post_url: str) -> Tuple[bool, str, Dict]:
        # print(f"📄 Fetching post page: {post_url}")

        try:
            headers = self.base_headers.copy()
            headers['Referer'] = 'https://www.facebook.com/'

            response = self.session.get(
                post_url,
                headers=headers,
                timeout=15,
                allow_redirects=True
            )
            # print(response.headers.get('Content-Type'))
            # print(response.headers.get('Content-Encoding'))

            if response.status_code != 200:
                return False, f"HTTP {response.status_code}", {}

            html = response.text
            # print(html)
            # with open("aa.html", "w") as f:
                # f.write(html)
            # Check if we're logged in
            if "login.php" in response.url or "Log In" in html.lower():return False, "Not logged in - cookies expired", {}

            params = {}
            fb_dtsg_patterns = [
                r'"DTSGInitData",\[\],{"token":"([^"]+)"',
                r'name="fb_dtsg" value="([^"]+)"',
                r'"fb_dtsg":"([^"]+)"',
                r'ft_ent_identifier":"([^"]+)"',
                r'"token":"([^"]{20,200})"',
            ]

            fb_dtsg = self._extract_from_html(html, fb_dtsg_patterns)
            if not fb_dtsg:return False, "Could not find fb_dtsg", {}
            params['fb_dtsg'] = fb_dtsg

            lsd_patterns = [
                r'"LSD",\[\],{"token":"([^"]+)"',
                r'"lsd":"([^"]+)"',
                r'LSD.*?token["\']:\s*["\']([^"\']+)',
            ]
            params['lsd'] = self._extract_from_html(html, lsd_patterns) or "Av0yXxabc123"

            params['jazoest'] = str(sum(ord(c) for c in fb_dtsg) % 100000)
            params['__rev'] = self._extract_from_html(html, [r'"revision":(\d+)', r'"__rev":(\d+)']) or "1031055084"
            params['__s'] = self._extract_from_html(html, [r'"__s":"([^"]+)"']) or "vhcdt2:k0s1cy:4til2p"
            params['__hsi'] = self._extract_from_html(html, [r'"hsi":"(\d+)"', r'"__hsi":"(\d+)"']) or "7583390057087405802"
            params['__spin_r'] = params['__rev']
            params['__spin_t'] = str(int(time.time()))

            # Extract feedback_id (CRITICAL)
            feedback_patterns = [
                r'"feedback_id":"([^"]+)"',
                r'ft_ent_identifier":"([^"]+)"',
                r'feedback:([^"]+)"',
            ]
            params['feedback_id'] = self._extract_from_html(html, feedback_patterns)
            if params['feedback_id']:
                decoded = base64.b64decode(params['feedback_id'].encode("utf-8")).decode("utf-8")
                currected = decoded if '_' not in decoded else decoded.split('_')[0]
                # print(decoded)
                # print(currected)
                params['feedback_id'] = base64.b64encode(f"{currected}".encode()).decode()

            if not params['feedback_id']:
                # Try to extract post ID and construct feedback_id
                post_id_match = re.search(r'post_id["\']:\s*["\'](\d+)', html)
                if post_id_match:
                    post_id = post_id_match.group(1)
                    encoded = base64.b64encode(f"feedback:{post_id if '_' not in post_id else post_id.split()[0]}".encode()).decode()
                    params['feedback_id'] = encoded
                else:
                    return False, "Could not find feedback_id or post_id", params

            # Store the HTML for debugging
            self.last_html = html

            # print(f"✅ Extracted parameters: {list(params.keys())}")
            return True, "", params

        except Exception as e:
            return False, f"Error fetching page: {str(e)}", {}

    def get_volatile_parameters(self, basic_params: Dict) -> Tuple[bool, str, Dict]:
        # """
        # Get volatile parameters (__dyn, __csr, etc.) by making a test request.

        # These parameters change frequently and must be fetched fresh.
        # """
        # print("🔄 Fetching volatile parameters...")

        try:
            # Prepare a test request to get fresh volatile params
            headers = {
                'accept': '*/*',
                'accept-language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,mr;q=0.6',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://www.facebook.com',
                'referer': 'https://www.facebook.com/',
                'user-agent': self.user_agent,
                'x-asbd-id': '359341',
                'x-fb-friendly-name': 'CometUFILiveTypingBroadcastMutation_StartMutation',
                'x-fb-lsd': basic_params['lsd'],
            }
            # Use minimal test data - we just need the response to see what params Facebook expects
            test_data = {
                'av': self.user_id,
                '__user': self.user_id,
                '__a': '1',
                '__req': '1',
                '__hs': '20435.HYP:comet_pkg.2.1...0',
                'dpr': '1',
                '__ccg': 'EXCELLENT',
                '__rev': basic_params['__rev'],
                '__s': basic_params['__s'],
                '__hsi': basic_params['__hsi'],
                '__dyn': '7xeUjG...',  # Will be replaced by actual response
                '__csr': 'g9Y4Id...',  # Will be replaced by actual response
                '__hsdp': 'g4CAwK...',
                '__hblp': '1u442S...',
                '__sjsp': 'g4CAwK...',
                '__comet_req': '7',
                'fb_dtsg': basic_params['fb_dtsg'],
                'jazoest': basic_params['jazoest'],
                'lsd': basic_params['lsd'],
                '__spin_r': basic_params['__spin_r'],
                '__spin_b': 'trunk',
                '__spin_t': basic_params['__spin_t'],
                '__crn': 'comet.fbweb.CometSinglePostDialogRoute',
                'fb_api_caller_class': 'RelayModern',
                'fb_api_req_friendly_name': 'CometUFILiveTypingBroadcastMutation_StartMutation',
                'server_timestamps': 'true',
                'variables': json.dumps({
                    "input": {
                        "feedback_id": basic_params['feedback_id'],
                        "session_id": str(uuid.uuid4()),
                        "actor_id": self.user_id,
                        "client_mutation_id": "1"
                    }
                }),
                'doc_id': '9815271091886179',
            }

            # Try to make the request
            response = self.session.post(
                'https://www.facebook.com/api/graphql/',
                headers=headers,
                data=test_data,
                timeout=15
            )

            if response.status_code == 200:
                # Even if we get an error, we might have gotten fresh volatile params
                # Look for them in the response text or in the request we just made
                # For now, we'll use known working patterns

                volatile_params = {
                    '__dyn': '7xeUjGU9k9wxxt0koC8G6Ejh941twWwIxu13wFw_DyUJ3odF8vyUco2qwJyEiwsobo6u3y4o27wywn82nwb-q7oc81EEc87m2210wEwgo9oO0wE7u12wOx62G5Usw9m1cwLwBgK7o8o4u1uwoE4G17yovwRwlE-U2exi4UaEW4UmwkUtxGm2SU4i5oe8cEW4-5pUfEdK2616DBx_wHwoE2mwLyEbUGdG1QwVwwwOg2cwMwhA4UjyUaUbGxe6Uak0zXxS9wkopg4-6o4e4UO2m3Gfxm2yVU-4FqwIK6E4-mEbUaU2wwgo620XEaUcEK6EqwaW9w',
                    '__csr': 'g9Y4IdPNtNkvd2YI8n19b5jl4mD6889R6FlqfPONuxq6hnkj4kIzBcgJrZiRjWRTJiAbQQBb9ZipioEOTuVU_iXQnf8F7RjSFKR_CjjZd2eRFW-FbLF9ai-QRoyHGLiIxRG8m_HHX-9WuF4V9QrydLjJeGjBqBVqHBFejhEmV9qV2a-mjCLKGKFbhFFFQinjBHGUhXxuEJa4XG8Ujh994bADhomDxm58jyEhyFeGijDABDy4umFoKjAyV8-EGBzayFoSESngOp192Q44V9UKFVUy5EaUsybz9V9oC8Guqd-Jd2UN4xy9_z8CK26ieWxqUCmaglzQ5eHADAK4olxa2u4EK4oN4glzU9pubGmbGUgyUObyWBKqnADAjzUgxd1maAzUhgkwxhZ2U84Usy98cEuxm9y98lzQ10-3Gm58Za3iezU6u2V0RwEyoS1zxm8B8EK3ubwRy5zU2gwi89E4N0SS2WE3rxq8Awqe0wUG2i68Ci78aKSO08u7KrzUuAAwF24xqabKFrCAoZ0FDg6C5p8bku6UB0se221eyUiwLxC9wyjA9h9o5W2q1LxGS71w5W29b-4FU-dGdwxxibCXwLwBG1Byo8EyczXg-ax57w1uC0ceyo5a9w9oj4UClWDykAr8E0ICU10VE3Cw1ambxq0fUw73G5E1l40gq4o2dgJ1Ax5wpE0UCJ04BwdN0ho5W17w9S0geahrG9wgU2iyAcw1qWE0E9011cpvw3uk02jm03ikFS05Fox03GoStw1Rq1kwam0J204kw8Nw4LxS0N20cu11wdKElgoUbo7MEqw5sxK09HofO0dm9gOgE36wprw3C20pEnw7jw42wi616x6oC17yk4Afw4yWK0t3x6cwcytG09Kov81Sw6Bw4XwrU5mm0L87O0ky4E14ui2m3iazajg2xo9oF6w2G810WAho3IyfyhonwsU3DAy80ueBbg0DKea12wu9o1a8jw16e16zUlwJgc8kw1MC6U1_8jJwjS7o0VG1vwNw67Dsg0ou7m0te0pW3m4o5-69US3KF5USm04n8C0jy3B1lG0TUeo4m0YE4K',
                    '__hsdp': 'gai1Wy8bA1rf4IiwywQgkxykioa8og6-gcgg8qoqxi8xc89aPN4Y55glQx0GojMLb7OR6A8yNsegFEd8JsjOOEihBF9yBaz5nh295iQtYmb8y6qFEMyzGBbjjid7qHv9Zl8ppRGsG2xT7mgRcdmzV7OpyamiW598FN2i3G4F9ahThqr17iNp56GmYF0MbJ9yMChRdfKTjaPfh99biBaO4ipbACAh948ijGQizejqAB4CgoXG8hozwAsNpogmohhENGAb8fQmV4EBDaimfjy9pFQkN94A5oVHoyGGF5wyGFaul6a9hAl29VbmGhqGHAlGlLtxWqpeqEDcaxq944yFEPL8cBKcpGGdxpmuNyByFpVpoAwy9n4xidFx11W4pVoUFAex1pq4q8262ry7Wh4t9J3olzVE-fwACjpFUZe5e2Cu6EKVoG5UO3d39VUCcy8Oi2qdGfzVqgkwKG1cgSaAx9a5KQdyQ9hbzy6QG2YHwFyqwwAyoDG11CwwwlUhgpwKyEeQ6U6Wu0PRwgEW3GayVRlxh_ki0x84S3-1uwsEazwKWwKwtUjzo4Ve6aw8Z0HwBwEK2C4URlw9Obx2aBo2cxe5axJh3wPz6tlw9e0yUrwPxa3O2F2414wFyUe8bo2dwba1Jwr84C1fxK0-Etypo5O1qK0g6261mwoEeogxS5XyUfEW0B83uw9q6813o2NUdooBwyhE7G3a0iq09ZweS2K2Kq7awuU3-g29xq7E2Bw5Fwn8kBzUfVUlwso4K8xm15wwyF8sgmKayEgVodU6i1Ew8q2a4Gxi0iO1EwnE4u6odE5W12wio3hx-0yEmwrUdo8olG6EK1YzE2rwKg8EuwQwmo7C3y1uwj84S698jx-3m322O2p2qzE7iUK15wlo6C1owKwgUS1JyElwdGbw7SybwWCxjwby2G3G0JU6e2q9wl84m',
                    '__hblp': '1yfgbomzoy3S0zoaExw8-1wx2uUbFo8E4iawTwXwroG3a14wxCwDwrE88yUfQ264E2cwwwPKi3W0y82ixeexm3G2CaK2S598-3iELCxu5UC5UdU6K3i8w8uu10yV8vK0BEbU4m4Uiwio3SxCu363W8xC0wEbUbu2G68W2a2C3O9Awi888cU8Uiwi8kwNxO1KDwPl09p0l83Tw9a442a0Ao4G0Yo88eQ7agdU5p0Hxa3-3qqdl0nEfUK483bxW0nK6U4q3O2K1UwrE1z98886O10y85u4UeoW1Ewi8tzU4a6oaoiwxwEzU6m1WxW6E9E6a2e2q3mU26w-x60gC19wUxy2S0TU2Ey8dUuwywp8tG2-1Wyo2xwrbm4U6a1iwhojwqU2bw9C2K8z8O7EszFEsG7U2exW0x82KyogxW0Fo6q4osGE2ywGwCwRx2Xx68wSDyoK2q7ob84K7E76i745HwEwZwp86y2Ofwio8EiG2u0L85mq1EwhUmwhUpwSwTwCwgE4C4Eng6-3m7C6UgwEzQ2a5EK1RCxui2CdF1CbBwrVEW1jwwxF162t0ygtyoyi1SxO1swUDwQx22u5UiyE2vzU9ocbwxGU9A9GewpENebw-V8swUwoUdoa8bEdoSdwVw-xm0SEK17wuVo2hwg85C8K2y4pEkUox20zEaEeEpwTK1xwoU9EC1kwhoO',
                    '__sjsp': 'gai1Wy8bA1rf4IiwywQgkxykioa8og6-gcgg8qpEgxi8xd8oAHf4jML25gPb5Qx0hfYbONYJhFuyNsegFEd8JsjRkG8QmqACakGclt489iUykmbQS8GCIwyzGBaHhPhSnv9Jlmp2KEW8x5x17qghxp7Az6FoyimUpwOxG2hwKzE8FQ2t28Ze5e2111092m0wUW4A4Q2-6Ee80-K0aNg1uU',
                }

                # print("✅ Got volatile parameters")
                return True, "", volatile_params

            else:
                return False, f"Failed to get volatile params: HTTP {response.status_code}", {}

        except Exception as e:
            return False, f"Error getting volatile params: {str(e)}", {}

    def send_typing_indicator(self, basic_params: Dict, volatile_params: Dict) -> Tuple[bool, str, str]:
        # """Send typing indicator to Facebook."""
        # print("⌨️  Sending typing indicator...")

        self.request_counter += 1
        # print("ddddd", self.ua_parts)
        headers = {
            'accept': '*/*',
            'accept-language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,mr;q=0.6',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.facebook.com',
            'priority': 'u=1, i',
            # 'referer': 'https://www.facebook.com/',
            # 'referer': 'https://www.facebook.com/share/1BWqDnrwJ7/',
            'referer': self.post_link,
            'sec-ch-prefers-color-scheme': 'dark',            
            'sec-ch-ua': self.ua_parts["sec_ch_ua"],
            'sec-ch-ua-full-version-list': self.ua_parts["sec_ch_ua_full_version_list"],
            'sec-ch-ua-mobile': self.ua_parts["sec_ch_ua_mobile"],
            'sec-ch-ua-model': '""',
            'sec-ch-ua-platform': self.ua_parts["sec_ch_ua_platform"],
            'sec-ch-ua-platform-version':self.ua_parts["sec_ch_ua_platform_version"],
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-asbd-id': '359341',
            'x-fb-friendly-name': 'CometUFILiveTypingBroadcastMutation_StartMutation',
            'x-fb-lsd': basic_params['lsd'],
        }

        session_id = str(uuid.uuid4())

        data = {
            'av': self.user_id,
            '__aaid': '0',
            '__user': self.user_id,
            '__a': '1',
            # Convert to hex like '1', '2', '3'
            '__req': hex(self.request_counter)[2:],
            '__hs': '20435.HYP:comet_pkg.2.1...0',
            'dpr': '1',
            '__ccg': 'EXCELLENT',
            '__rev': basic_params['__rev'],
            '__s': basic_params['__s'],
            '__hsi': basic_params['__hsi'],
            '__dyn': volatile_params['__dyn'],
            '__csr': volatile_params['__csr'],
            '__hsdp': volatile_params['__hsdp'],
            '__hblp': volatile_params['__hblp'],
            '__sjsp': volatile_params['__sjsp'],
            '__comet_req': '15',
            'fb_dtsg': basic_params['fb_dtsg'],
            'jazoest': basic_params['jazoest'],
            'lsd': basic_params['lsd'],
            '__spin_r': basic_params['__spin_r'],
            '__spin_b': 'trunk',
            '__spin_t': basic_params['__spin_t'],
            '__crn': 'comet.fbweb.CometSinglePostDialogRoute',
            'fb_api_caller_class': 'RelayModern',
            'fb_api_req_friendly_name': 'CometUFILiveTypingBroadcastMutation_StartMutation',
            'server_timestamps': 'true',
            'variables': json.dumps({
                "input": {
                    "feedback_id": basic_params['feedback_id'],
                    "session_id": session_id,
                    "actor_id": self.user_id,
                    "client_mutation_id": str(self.request_counter)
                }
            }),
            'doc_id': '9815271091886179',
        }

        try:
            response = self.session.post(
                'https://www.facebook.com/api/graphql/',
                headers=headers,
                data=data,
                timeout=15
            )

            if response.status_code == 200:
                # Remove "for (;;);" prefix
                response_text = response.text
                if response_text.startswith("for (;;);"):
                    response_text = response_text[9:]

                try:
                    result = json.loads(response_text)
                    if 'errors' in result:
                        return False, f"Typing error: {result['errors'][0].get('message', 'Unknown')}", ""

                    print("✅ Typing indicator sent")
                    return True, "", session_id

                except json.JSONDecodeError:
                    return True, "", session_id  # Still consider it successful for session_id

            else:
                return False, f"HTTP {response.status_code}", ""

        except Exception as e:
            return False, f"Error: {str(e)}", ""

    def post_comment(self, basic_params: Dict, volatile_params: Dict,session_id: str, comment_text: str) -> Tuple[bool, str, Dict]:

        self.request_counter += 1

        headers = {
            'accept': '*/*',
            'accept-language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,mr;q=0.6',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.facebook.com',
            'priority': 'u=1, i',
            'referer': 'https://www.facebook.com/',
            'sec-ch-prefers-color-scheme': 'dark',
            'sec-ch-ua': self.ua_parts["sec_ch_ua"],
            'sec-ch-ua-full-version-list': self.ua_parts["sec_ch_ua_full_version_list"],
            'sec-ch-ua-mobile': self.ua_parts["sec_ch_ua_mobile"],
            'sec-ch-ua-model': '""',
            'sec-ch-ua-platform': self.ua_parts["sec_ch_ua_platform"],
            'sec-ch-ua-platform-version': self.ua_parts["sec_ch_ua_platform_version"],
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.user_agent,
            'x-asbd-id': '359341',
            'x-fb-friendly-name': 'useCometUFICreateCommentMutation',
            'x-fb-lsd': basic_params['lsd'],
        }

        current_time = int(time.time() * 1000)
        # print("this is hear ",basic_params['feedback_id'],)
        data = {
            'av': self.user_id if not self.i_user else self.i_user,
            '__aaid': '0',
            '__user': self.user_id if not self.i_user else self.i_user,
            '__a': '1',
            '__req': hex(self.request_counter)[2:],
            '__hs': '20435.HYP:comet_pkg.2.1...0',
            'dpr': '1',
            '__ccg': 'EXCELLENT',
            '__rev': basic_params['__rev'],
            '__s': basic_params['__s'],
            '__hsi': basic_params['__hsi'],
            '__dyn': volatile_params['__dyn'],
            '__csr': volatile_params['__csr'],
            '__hsdp': volatile_params['__hsdp'],
            '__hblp': volatile_params['__hblp'],
            '__sjsp': volatile_params['__sjsp'],
            '__comet_req': '15',
            'fb_dtsg': basic_params['fb_dtsg'],
            'jazoest': basic_params['jazoest'],
            'lsd': basic_params['lsd'],
            '__spin_r': basic_params['__spin_r'],
            '__spin_b': 'trunk',
            '__spin_t': basic_params['__spin_t'],
            '__crn': 'comet.fbweb.CometSinglePostDialogRoute',
            'fb_api_caller_class': 'RelayModern',
            'fb_api_req_friendly_name': 'useCometUFICreateCommentMutation',
            'server_timestamps': 'true',
            'variables': json.dumps({
                "feedLocation": "POST_PERMALINK_DIALOG",
                "feedbackSource": 2,
                "groupID": None,
                "input": {
                    "client_mutation_id": str(self.request_counter),
                    "actor_id": self.user_id if not self.i_user else self.i_user,
                    "attachments": None,
                    "feedback_id": basic_params['feedback_id'],
                    "formatting_style": None,
                    "message": {
                        "ranges": [],
                        "text": comment_text
                    },
                    "reply_target_clicked": False,
                    "attribution_id_v2": f"CometSinglePostDialogRoot.react,comet.post.single_dialog,via_cold_start,{current_time},491588,,,",
                    "vod_video_timestamp": None,
                    "is_tracking_encrypted": True,
                    "tracking": [
                        json.dumps({
                            "assistant_caller": "comet_above_composer",
                            "conversation_guide_session_id": str(uuid.uuid4()),
                            "conversation_guide_shown": None
                        })
                    ],
                    "feedback_source": "OBJECT",
                    "idempotence_token": f"client:{str(uuid.uuid4())}",
                    "session_id": session_id,
                    "downstream_share_session_id": str(uuid.uuid4()),
                    "downstream_share_session_origin_uri": self.post_link,
                    "downstream_share_session_start_time": str(current_time - 100)
                },
                "inviteShortLinkKey": None,
                "renderLocation": None,
                "scale": 1,
                "useDefaultActor": False,
                "focusCommentID": None,
                "__relay_internal__pv__CometUFICommentAvatarStickerAnimatedImagerelayprovider": False,
                "__relay_internal__pv__IsWorkUserrelayprovider": False
            }),
            'doc_id': '24615176934823390',
        }

        try:
            # print(basic_params['feedback_id'])
            response = self.session.post(
                'https://www.facebook.com/api/graphql/',
                headers=headers,
                data=data,
                timeout=15
            )

            response_text = response.text
            # print(response_text)
            if response_text.startswith("for (;;);"):
                response_text = response_text[9:]

            if response.status_code == 200:
                try:
                    result = json.loads(response_text)
                    with open("aa.json", "w") as a:
                        json.dump(result, a, indent=2)
                    if 'errors' in result:
                        error_msg = result['errors'][0].get(
                            'message', 'Unknown error')
                        return False, error_msg, result
                    # data.comment_create.feedback_comment_edge.node.id
                    if isinstance(result, dict):
                        data = result.get("data", {})
                        comment_create = data.get("comment_create", {})
                        
                        comment = comment_create.get("feedback_comment_edge", {}).get("node", {})
                        comment_id = comment.get("id")

                        if comment_id:
                            # print(f"✅ Comment posted successfully! ID: {comment_id}")
                            return True, comment_id, result

                    return False, "Unexpected response format", result


                except json.JSONDecodeError:
                    return False, "Invalid JSON response", {"text": response_text[:200]}

            else:
                return False, f"HTTP {response.status_code}", {"text": response_text[:200]}

        except Exception as e:
            return False, f"Error: {str(e)}", {}

    def execute_comment(self, post_url: str, comment_text: str) -> Tuple[bool, str, Dict]:
        success, error, basic_params = self.fetch_post_page(post_url)
        if not success:
            return False, f"Failed to fetch page: {error}", {}

        # Step 2: Get volatile parameters
        success, error, volatile_params = self.get_volatile_parameters(
            basic_params)
        if not success:
            # print(f"⚠ Warning: Using fallback volatile params: {error}")
            # Use fallback volatile params
            volatile_params = self.volatile_params

        # Step 3: Send typing indicator
        time.sleep(1)  # Small delay
        success, error, session_id = self.send_typing_indicator(basic_params, volatile_params)
        if not success:
            # print(f"⚠ Typing indicator failed: {error}")
            # Continue anyway with a generated session_id
            session_id = str(uuid.uuid4())

        # Step 4: Post the actual comment
        time.sleep(1)  # Mimic human typing delay
        success, result, full_response = self.post_comment(
            basic_params, volatile_params, session_id, comment_text
        )

        if success:
            print(f"\n🎉 Success! Comment posted with ID: {result}")
        else:
            print(f"\n❌ Failed: {result}")

        return success, result, full_response


# # ============================================================================
# # MAIN EXECUTION - EXAMPLE USAGE
# # ============================================================================

# if __name__ == "__main__":
#     # Your Facebook cookies (replace with your actual cookies)
#     COOKIES = '''
# datr=OZ4oaaPMapVsAMgQ-kctLHAf; fr=1pXZrWFE4HqVWV2wj.AWejfeSTh--N3PulYdY5Tpt94ymCXqn_KwOcD9Gak4vn1geUPAY.BpPvJN..AAA.0.0.BpPvJN.AWfhqEC1Jxqa2Sc0mxTIO2Y1csM; sb=OZ4oaetTZUNpwQtVht7HwxCu; wd=588x479; dpr=1.6800000667572021; locale=en_US; ps_l=1; ps_n=1; c_user=61558074221758; xs=41%3AwPxC4m9Aw-KdHw%3A2%3A1765119401%3A-1%3A-1%3A%3AAcySD8XTcwi2Vxf7cA3VX--_s5yQSgMBTdkjY7CBhQ; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1765732966716%2C%22v%22%3A1%7D
#     '''

#     # Initialize the bot
#     bot = FacebookCommentBot(COOKIES)

#     # Post to comment on
#     POST_URL = "https://www.facebook.com/share/1AkJY1hLLP/"

#     # Comment text
#     COMMENT = "CMT by Hacker!"

#     # Execute the comment
#     success, result, response = bot.execute_comment(POST_URL, COMMENT)

#     # Print result
#     print("\n" + "="*60)
#     if success:
#         print(f"✅ SUCCESS: Comment ID: {result}")
#     else:
#         print(f"❌ FAILED: {result}")
#         if response:
#             print(f"Response: {json.dumps(response, indent=2)[:500]}...")
#     print("="*60)
