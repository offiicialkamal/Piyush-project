import requests
import re


def get_fb_post_id(url: str) -> str:
    r = requests.get(url)
    r.raise_for_status()

    patterns = [
        r"/posts/[^/]+/(\d+)",
        r"/posts/(\d+)",
        r"story_fbid=(\d+)",
        r"/permalink/(\d+)",
    ]

    for p in patterns:
        m = re.search(p, r.text)
        if m:
            return m.group(1)

    raise RuntimeError("Post ID not found")


id = get_fb_post_id("https://www.facebook.com/share/1Efe621hDM/")
print(id)
