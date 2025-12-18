import re, sys
import json
import threading
import requests
# from file_handlers import read_json
from .general import generalFunctions
from .general import Admin1
from .general import FacebookCommentBot



class run_single(threading.Thread, generalFunctions, Admin1, FacebookCommentBot):
    def __init__(self, cookie, post_link, comment, comment_per_acc, options, result_container):
        super().__init__()
        self.__userAgent = cookie.get(list(cookie.keys())[0])[0]
        self.__cookie = generalFunctions().refactorCookie(list(cookie.keys())[0])
        self.__post_link = post_link
        self.__comment = comment
        self.__comment_per_acc = comment_per_acc
        self.__options = options
        self.result_container = result_container
        
        ## class specific variables
        self.__pagesURL = "https://www.facebook.com/pages/?category=your_page"
        self.__tokens = {}
        self.__all_profiles = {}
        self.__main_user_id = self.__cookie.get("c_user")

    def run(self):
        print(self.__options)
        # print("started threed")
        try:
            # print(self.__cookie)
            # print()
            # print(self.__userAgent)
            # sys.exit()
            ######################################################################################################################
            ######################################################################################################################
            ############# TILL NOW EVERYTHING IS WORKING #########################################################################
            ########################### THIS IS THE MAIN PART OF THE PROGRAM #####################################################
            ##                                                                                                                  ##
            ## EXTRACT THE TOKENS AND SET TO INSTANCE                                                                           ##
            ## ======>>>>>>>>>> IF LOGIN FAILED / CHECKPOINT TAKE EXIT ==>> IN FUTURE THAT COOKIE IS USEFULL FOR CLEANUP        ##
            ##                                                                                                                  ##
            ## EXTRACT THE POST PAGE DATA                                                                                       ## 
            ##                                                                                                                  ##
            ## IF USER WANT COMMENT BY PAGE ====>>>> Extract PAGES                                                              ##
            ##=============>>>> CREATE AN LIST OOF PAGES                                                                        ##
            ##=============>>>> LOOP THROUGH IT AND POST COMMENTS ONE BY ONE ACCORDING TO THE COMMENT_PER_ACC VARIABLE          ##
            ## ELSE ACCORDING TO THE COMMENT_PER_ACC VARIABLE LOOP POST COMMENT N TIMES USING MAIN ID                           ##
            ##                                                                                                                  ##
            ######################################################################################################################
            ######################################################################################################################
            ######################################################################################################################
            ######################################################################################################################
        ######## STEP 1
            params, fresh_cookies = self.extract_params_from_page(self.__cookie, self.__pagesURL, self.__userAgent)
            print(params)
            # print()
            # print(fresh_cookies)
            # sys.exit()
        ######## STEP 2
            if params:
                self.__tokens = params
                if self.__options['from_page']:
                    response = self.fetch_pages(params, fresh_cookies, self.__userAgent)
                    print(response)
                if self.__options['from_user']:
                    self.__all_profiles[self.__cookie['c_user']] = 'Name'
                
                print(self.__all_profiles)
                for user in self.__all_profiles.keys():
                    # UID = user
                    self.__cookie["i_user"] = '61585351100418'
                    cookie = self.__cookie
                    user_agent = self.__userAgent
                    post_link = self.__post_link
                    comment = self.__comment
                    tokens = self.__tokens
                    print(self.__cookie)
                    for _ in range(self.__comment_per_acc):
                        bot = FacebookCommentBot(cookie, user_agent)
                        success, result, response = bot.execute_comment(post_link, comment)
                        # now validate 
                        # print("\n" + "="*60)
                        if success:
                            print(f"✅ SUCCESS: Comment ID: {result}")
                        else:
                            print(f"❌ FAILED: {result}")
                            if response:
                                print(f"Response: {json.dumps(response, indent=2)[:500]}...")
                        print("="*60)


                self.__all_profiles[self.__cookie['c_user']] = 'Name'
            else:
                ### pass mark acc as locked ( pass it to Queue )
                print("Failed to extract parameters MAY BE ACCOUNT IS ALREADY LOCKED")
                sys.exit()
                
        except Exception as e:
            print(f"An error occurred: {e}")
            import traceback
            traceback.print_exc()

