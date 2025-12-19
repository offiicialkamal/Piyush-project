import json
import base64
import re
from typing import Dict

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
        # print("sucessfully refactord cookies")
        return cokie_json


    def get_ua_parts(self, user_agent: str) -> Dict:
        platform_match = re.search(r"\((.*?)\)", user_agent)
        platform = platform_match.group(1) if platform_match else "Unknown Platform"

        browser_match = re.search(
            r"(Chrome|Safari|SamsungBrowser|Edge|Firefox|Opera|Vivaldi|UC Browser)/([\d.]+)",
            user_agent
        )

        if browser_match:
            browser_name = browser_match.group(1)
            browser_version = browser_match.group(2)
        else:
            browser_name = "Unknown Browser"
            browser_version = "Unknown Version"

        major = browser_version.split(".")[0]

        sec_ch_ua = f'"{browser_name}";v="{major}", "Not_A Brand";v="99"'
        sec_ch_ua_full_version_list = f'"{browser_name}";v="{browser_version}", "Not_A Brand";v="99.0.0.0"'
        sec_ch_ua_mobile = "?1" if "Mobile" in user_agent else "?0"

        if "Windows NT" in platform:
            sec_ch_ua_platform = '"Windows"'
            sec_ch_ua_platform_version = '"' + platform.split("Windows NT ")[1].split(";")[0] + '"'
        elif "Mac OS X" in platform:
            sec_ch_ua_platform = '"macOS"'
            sec_ch_ua_platform_version = '"' + platform.split("Mac OS X ")[1] + '"'
        elif "Linux" in platform:
            sec_ch_ua_platform = '"Linux"'
            sec_ch_ua_platform_version = '""'
        else:
            sec_ch_ua_platform = '"Unknown"'
            sec_ch_ua_platform_version = '""'

        return {
            "platform": platform,
            "browser_name": browser_name,
            "browser_version": browser_version,
            "sec_ch_ua": sec_ch_ua,
            "sec_ch_ua_full_version_list": sec_ch_ua_full_version_list,
            "sec_ch_ua_mobile": sec_ch_ua_mobile,
            "sec_ch_ua_platform": sec_ch_ua_platform,
            "sec_ch_ua_platform_version": sec_ch_ua_platform_version
        }
