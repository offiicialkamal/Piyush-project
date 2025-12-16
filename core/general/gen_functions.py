import json


class generalFunctions:
    """contains alll small and general functions"""

    def __init__(self):
        pass

    def refactorCookie(self, cookie):
        cokie_json = {}
        li = cookie.split(';')
        for ele in li:
            ele = ele.strip().split('=')
            if len(ele) == 2:
                name = ele[0]
                value = ele[1]
                cokie_json[name] = value
        print("sucessfully refactord cookies")
        return cokie_json

    def fetch_pages(self, params, cookies):
        headers = {
            'accept': '*/*',
            'accept-language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,mr;q=0.6',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.facebook.com',
            'priority': 'u=1, i',
            'referer': 'https://www.facebook.com/pages/?category=your_page',
            'sec-ch-prefers-color-scheme': 'dark',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-full-version-list': '"Chromium";v="142.0.7444.176", "Google Chrome";v="142.0.7444.176", "Not_A Brand";v="99.0.0.0"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-model': '""',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua-platform-version': '"19.0.0"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.__userAgent,
            'x-asbd-id': '359341',
            'x-fb-friendly-name': 'PagesCometLaunchpointUnifiedQueryPagesListRedesignedQuery',
        }

        # Get lsd from params or generate from cookies
        if 'lsd' not in params and 'lsd' in headers.get('x-fb-lsd', ''):
            params['lsd'] = headers['x-fb-lsd']
        elif 'lsd' not in params:
            # Try to extract from cookie jar if available
            pass

        # Build the data payload
        data = {
            'av': cookies['c_user'],
            '__aaid': '0',
            '__user': cookies['c_user'],
            '__a': '1',
            '__req': '1x',
            '__hs': '20435.HCSV2:comet_pkg.2.1...0',
            'dpr': '1',
            '__ccg': 'EXCELLENT',
            '__rev': '1031049534',
            '__hsi': params.get('__hsi', '7583267513849929814'),
            '__dyn': '7xeUjGU5a5Q1ryaxG4Vp41twWwIxu13wFwhUngS3q2ibwNw9G2Sawba1DwUx60GE3Qwb-q7oc81EEc87m221Fwgo9oO0n24oaEnxO1Nwzwv89kbxS1Fwc61awhUC7Udo5qfK0zEkxe2GewGwkUe9obrwh8lwUwOzEjUlDw-wUwxwjFovUaU6a0BEbUG2-azqwt8eo5d08O321LyUaUbGxe6Uak0zU8oC1Hg6C13xecwBwUU-4rwEKufxamEbbxG1fBG2-2K0E8461wweW2K3abxG6E2Uw',
            '__csr': 'gbQ_4Yj5hthcIgxtPYO9kn5iNcKTd7jRbb5OiRiYlkzsOiiiiOsTEBGTqiRYl6OPp5rmJGnCZmn8FLBlbVXLAh3cQV9k8G_yuaFehFBXFSuFRp4ld9lCKXjGqUF95KdqQV95qDVmh5JpFXyGDiQcgCjAAHgxGiALQHhVeEZ2GBzEN1fiXheqiKUkxmh28-VUgypprCCAgxrBAiGHG9O1WaBx6F9F5Aohx6q9DAzqCzUKlkvAAogmEN1Sijh8MFEgUxqUtyAbiAQiUOQp5zF8OGyp8tK9Cp89ojG6pp8dFpkEkz8gwzXybAy9F8DxOq48WmqWye9xaqbzFEcEWqUgxa5UsxbyucyuuULwBxe26bg98K7Eb9oS8DzUnxKfCCwPyLGq8x2i7o6F0QwHyVohxm48vm7UjwlFEd85O2218xe1ew8e0jibwaK19wxwfq1hBCyVUCrAyF8K9yQfAK5bGaxm9hU7K4o6J6wKyo4K5E4GUcE69160LU4R0J85WgGdxN0YwmFU25wxDVK2qfxu0z-01n4x21Iw0wkw0yQw6Mw09ty013go3Sg7e1mgGm079U20xO0EpC0baDg48w0Am08Tw4BwhS0z8jw4mwaGUJ0GDt5xu1Zy41Vw17a0ze0u-0Lz4ykcB80B80n4w4pw6DykcDg5606eo0vboy9zo2YG04nE3Jwmo0k_w2xo0p2w1cu5E88gDg0hiw2Hk0lC3C8g3nwDyo1fU',
            '__hsdp': 'gjJ9i1OC5Ep49aGqEGcgkxq8xxOG89Qx3cy9EliIWcx7qq8D5892ha1eUMRvfaCCtFNWpycy8GeFN2jR8Fhvag8sp1f9sHx5OqMZ4W31a4EQ4krT3n8FbaxahsxUyPKumy48piAl7qEzc7HpaRQoGat98aF34lkjKcy29y4EnzCbR4O28Fel6aiF8MCWyj764EQcaYkxzslsadNhF1oxEOQMKbQe4j8yFPP6AHO4u_XJ4BjrAFGq8gGUjyameyoSpK7b_GVRxqioECbOy1h31Fafxiii9CGEy2C4HzE-rx97EUOeFe8G2kx9oIxVm4A8x2uHAw_GGhIMW2C5HENogg8o8Ea8umQayF8KbAq4583a2sUB0zgAwe8ll1aagIgUcoG6S6oDXQ21Dga8yUhz8kxGq1hpN0gAAwwPK48B12dz5hBQ5oS68Oez-dK2y7axabyebK8gZ0Hhbji3FpEqwXDyXxW5ocpsg3p0iUK369K6O0t86C1rx27UdEb8C7Q8gmlfwcjxqt2E889o2UeQ2bK19jw8C3e78aocErw-goyk2Ro5-EGdwVUhH83ibg9EbGiwcK0GobUy15w8a1Jz4Wg6Gcw6gU24wlEaU760YolxO8wnE5S1ryo0xC5o0xi0z8K0cxwhU1OU0kaw8S1Ewfa2S3u3a0yo0IW2218wkU1Uo5m1Pw26U17E1uoc8f83mw2JU2tw4Yw5Gwbi08jwam0vq7E',
            '__hblp': '1u3-2q14w922u0gSVE98S2u5EdU3xy8423q263e1EwBy86e0LUcoS3C0AU10o-4EfUsKdwRyUf8W3O4o6S5EdE5W4UdUvxeE2WxW1CwAw5awt87K4oa8swGUKcg3DxW1gBwSwNxGbDwFyrxO1Sxy1gw6dwvE790Fw9a0woO321Kz8swn85F0h84e2W68douxG2q2u1pwiU6u0hq0VU2Cw4HzE1aoaUcU4q0W9EW0K8apU88cE4-bx60iu19wgUlx-1VxKU7Cawdm19wjEdo5S5oW786C0LE8Urxu361-xCfwqo1rooxa16wf-0DU4m1cwi86i1twnE6-6FUiway1Awq85u2Ci2C11xadz8dVUaE29yHHw8G0i2ewai1qwwwGxS1jw7xwOBxO6u1nw54wMwmorxi6E-5oC1gwEwda0WA2Z0LwYCwmo4K2a1tw9q0m61ixi0x8qwcG19wBxe1rgowqU7i0J87u0SU2_g2Aw-xy0pW7Esxu',
            '__sjsp': 'gjJ9i1OC5Ep49aGqEGcgkxq8xxOG89Qx39ykyrQHez8hSCy98kwA94E4Xz3lYYGqpQhhWpy4qmGiqy3FfkyB9dOA6nNBMBNQBOK4n9H2QYjEc4EizghhLsdsyAIF4QAn8u8IXzq8gxBahoB58Ox-dRyCOyaic4kchlheUO88dgqzCbwGBgCmuc9K1ji8iWa1EwCUcUS5VVrh9kezEeUoxq2jCKt1yi9xDxsMqiwFzFEe8mzE-6Q7ohzqwBVpoIxVu3Oi3-GwwwkEcU4K2q0H8K0w5giyA1Lo9U2swce2e2-um5oS68rz-dK1DxG8wuo5qubK3i36n408e3S9xYw3uwmUgx-3q2O9xZ2o3BUmDgG220W41Ojw44w8S6o2rG1iUhH83ibg1QEbUy15wf2cjF018O78y',
            '__comet_req': '15',
            'fb_dtsg': params.get('fb_dtsg', 'NAfuexDc3N4ocAvxlOqZ5muhmF9RaYzUHxRfc9U0qYD6zLIptx-Twbg:2:1765610686'),
            'jazoest': params.get('jazoest', '25677'),
            'lsd': params.get('lsd', '62GJJYDgTg-jMe1ah3qI9c'),
            '__spin_r': '1031049534',
            '__spin_b': 'trunk',
            '__spin_t': '1765617056',
            '__crn': 'comet.fbweb.PageCometLaunchpointDiscoverRoute',
            'fb_api_caller_class': 'RelayModern',
            'fb_api_ref_class': 'RelayModern',
            'fb_api_req_friendly_name': 'PagesCometLaunchpointUnifiedQueryPagesListRedesignedQuery',
            'server_timestamps': 'true',
            'variables': '{"scale":1}',
            'doc_id': '25166087866410074',
        }

        # Add __s parameter if found
        if '__s' in params:
            data['__s'] = params['__s']

        # Set the lsd in headers
        if 'lsd' in params:
            headers['x-fb-lsd'] = params['lsd']

        response = requests.post(
            'https://www.facebook.com/api/graphql/',
            cookies=cookies,
            headers=headers,
            data=data
        )

        return response

    def extract_params_from_page(self, pageURL):
        global cookies
        # First, fetch the main page to get fresh parameters
        main_page_url = pageURL
        # cookie = format_cookie('vpd=v1%3B955x426x1.6875; pas=61564971251642%3A3lsIQzxXIw; fr=0unAOSi6yWfybLy7T.AWfLSnVmX35EkDGnDHwXibt8MrkBt6Al8hblGGjnR9MQZHxgzps.BpPVaS..AAA.0.0.BpPVaw.AWcIyCJUeSVRV9XLGoDiCN-iKjY; m_pixel_ratio=1.6875; locale=en_GB; fbl_st=100633974%3BT%3A29427126; xs=48%3AuUFoOvtkOFpd3w%3A2%3A1765627546%3A-1%3A-1; c_user=61564971251642; ps_n=1; sb=klY9ac_nRIs1y1aa7Kca2hlo; wd=427x956; wl_cbv=v2%3Bclient_version%3A3017%3Btimestamp%3A1765627568; ps_l=1; datr=klY9aXM9pdUcks3XTVsHSoKu;')
        # cookie = format_cookie('vpd=v1%3B955x426x1.6875; pas=100028085268481%3Ag12cPYTDlp; fr=03FG9b5R29NXRi5Lj.AWexyFgJiYjx8oTaxPUR0fmFpEc_i2B_SARlwNpSmFuMM0i5YVM.BpPUGw..AAA.0.0.BpPUHA.AWfBxKfap16jH-4aPTKuPvF0UV4; m_pixel_ratio=1.6875; locale=hi_IN; fbl_st=100434845%3BT%3A29427036; xs=27%3AU5TgH9fqYyFoUw%3A2%3A1765622200%3A-1%3A-1; wl_cbv=v2%3Bclient_version%3A3017%3Btimestamp%3A1765622208; c_user=100028085268481; sb=sEE9aerzdRizAtKuBGYpldOl; wd=427x956; datr=sEE9aT0RVLyqUxLhVQGv3EqK;')
        # cookie = format_cookie('vpd=v1%3B955x426x1.6875; pas=100055324832768%3AfAkbOISPFR; fr=02lHVC0GfPm0GiHcG.AWec4ljt0isVEy4To9tmoIqmAX3sCwkTXbKA4w8YVyo5ijp4BV0.BpPpE8..AAA.0.0.BpPpFJ.AWeqItanO9duFi2TEB7Hsmqgtx0; m_pixel_ratio=1.6875; locale=en_US; fbl_st=101738373%3BT%3A29428468; xs=35%3AvhrGQu_YI-0kxQ%3A2%3A1765708101%3A-1%3A-1; c_user=100055324832768; ps_n=1; sb=PJE-acmCRdqPMcYo6OW5FOcm; wd=427x956; wl_cbv=v2%3Bclient_version%3A3017%3Btimestamp%3A1765708105; ps_l=1; datr=PJE-aay-01lXogzj35eyLMA-;')
        cookies = self.__cookies
        session = requests.Session()
        session.cookies.update(cookies)

        headers = {
            # 'User-Agent': '',
            'user-Agent': self.__userAgent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,mr;q=0.6',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Upgrade-Insecure-Requests': '1',
        }

        # Get the main page
        response = session.get(main_page_url, headers=headers)

        if response.status_code != 200:
            print(f"Failed to fetch page: {response.status_code}")
            return None

        html = response.text
        # with open("hh.html", "w") as a:
        #     a.write(html)
        # Extract parameters using regex patterns
        params = {}

        # Extract fb_dtsg sometimes comes with meta tagas
        fb_dtsg_match = re.search(
            r'"DTSGInitData",\[\],{"token":"([^"]+)"', html)
        if not fb_dtsg_match:
            fb_dtsg_match = re.search(r'name="fb_dtsg" value="([^"]+)"', html)
        if not fb_dtsg_match:
            fb_dtsg_match = re.search(r'"fb_dtsg":"([^"]+)"', html)

        if fb_dtsg_match:
            params['fb_dtsg'] = fb_dtsg_match.group(1)
        else:
            print("Warning: Could not find fb_dtsg")

        lsd_match = re.search(r'"LSD",\[\],{"token":"([^"]+)"', html)
        if not lsd_match:
            lsd_match = re.search(r'"lsd":"([^"]+)"', html)

        if lsd_match:
            params['lsd'] = lsd_match.group(1)
        else:
            print("Warning: Could not find lsd")

        # jazoest_match = re.search(r'name="jazoest" value="(\d+)"', html)
        jazoest_match = re.search(r'jazoest=(\d+)"', html)
        if not jazoest_match:
            jazoest_match = re.search(r'"jazoest":"(\d+)"', html)

        if jazoest_match:
            params['jazoest'] = jazoest_match.group(1)
        else:
            print("Warning: Could not find jazoest")

        hsi_match = re.search(r'"hsi":"(\d+)"', html)
        if hsi_match:
            params['__hsi'] = hsi_match.group(1)

        s_match = re.search(r'"site_data":\{"s":"([^"]+)"', html)
        if s_match:
            params['__s'] = s_match.group(1)

        if '__s' not in params:
            script_match = re.search(r'__s":"([^"]+)"', html)
            if script_match:
                params['__s'] = script_match.group(1)

        return params, session.cookies.get_dict()
