import re
import json
import threading
import requests
# from file_handlers import read_json
from general.gen_functions import generalFunctions


class run_single(threading.Thread, generalFunctions, result_container):
    def __init__(self, cookie, post_link, comment, comment_per_acc, result_container):
        super().__init__()
        self.result_container = result_container
        self.__comment_per_acc = comment_per_acc
        self.__userAgent = 
        self.__cookies = general_funnctions.refactorCookie(cookie)
        ## class specific variables
        self.__pagesURL = "https://www.facebook.com/pages/?category=your_page"
        self.__tokens = {}

    def run(self):
        print("started threed")
        try:
            print("Extracting fresh parameters from Facebook page...")
            params, fresh_cookies = self.extract_params_from_page()

            if params:
                self.__tokens = params
                print(f"Extracted parameters: {list(params.keys())}")

                # Make the GraphQL request with fresh parameters
                print("\nMaking GraphQL request...")
                response = self.make_graphql_request(params, fresh_cookies)

                print(f"Response status: {response.status_code}")

                if response.status_code == 200:
                    try:
                        data = response.json()
                        # Save the response
                        with open('main.json', 'w') as f:
                            json.dump(data, f, indent=4)

                        # Extract profiles if available
                        if 'data' in data and 'viewer' in data['data']:
                            profiles = data['data']['viewer']['actor'].get(
                                'additional_profiles_with_biz_tools', {}).get('edges', {})
                            print(f"\nFound {len(profiles)} profiles:")
                            for profile in profiles:
                                profile = profile.get('node', {})
                                name = profile.get('name', 'N/A')
                                profile_id = profile.get('id', 'N/A')
                                print(f"{name}    {profile_id}")
                                print()
                        else:
                            print("No profiles found in response")
                            print("Response structure:",
                                  json.dumps(data, indent=2)[:500])

                    except json.JSONDecodeError as e:
                        print(f"Failed to parse JSON response: {e}")
                        print(f"Response text: {response.text[:500]}")
                else:
                    print(
                        f"Request failed with status: {response.status_code}")
                    print(f"Response: {response.text[:500]}")

            else:
                print("Failed to extract parameters MAY BE ACCOUNT IS ALREADY LOCKED")

        except Exception as e:
            print(f"An error occurred: {e}")
            import traceback
            traceback.print_exc()


cookie = "datr=OZ4oaaPMapVsAMgQ-kctLHAf; fr=1pXZrWFE4HqVWV2wj.AWejfeSTh--N3PulYdY5Tpt94ymCXqn_KwOcD9Gak4vn1geUPAY.BpPvJN..AAA.0.0.BpPvJN.AWfhqEC1Jxqa2Sc0mxTIO2Y1csM; sb=OZ4oaetTZUNpwQtVht7HwxCu; wd=588x479; dpr=1.6800000667572021; locale=en_US; ps_l=1; ps_n=1; c_user=61558074221758; xs=41%3AwPxC4m9Aw-KdHw%3A2%3A1765119401%3A-1%3A-1%3A%3AAcySD8XTcwi2Vxf7cA3VX--_s5yQSgMBTdkjY7CBhQ; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1765732966716%2C%22v%22%3A1%7D"
ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"

t = commenter(cookie, ua)
t.start()
