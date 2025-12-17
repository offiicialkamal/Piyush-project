import re, sys
import json
import threading
import requests
# from file_handlers import read_json
from .general import generalFunctions
from .general import Admin1



class run_single(threading.Thread, generalFunctions, Admin1):
    def __init__(self, cookie, post_link, comment, comment_per_acc, result_container):
        super().__init__()
        self.result_container = result_container
        self.__comment_per_acc = comment_per_acc
        self.__userAgent = cookie.get(list(cookie.keys())[0])[0]
        self.__cookie = generalFunctions().refactorCookie(list(cookie.keys())[0])
        ## class specific variables
        self.__pagesURL = "https://www.facebook.com/pages/?category=your_page"
        self.__tokens = {}

    def run(self):
        print("started threed")
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
            # print(params)
            # print()
            # print(fresh_cookies)
            # sys.exit()
        ######## STEP 2
            if params:
                self.__tokens = params
                print(f"Extracted parameters: {list(params.keys())}")

                # Make the GraphQL request with fresh parameters
                # print("\nMaking GraphQL request...")
                response = self.fetch_pages(params, fresh_cookies, self.__userAgent)
                print(response)

                # print(f"Response status: {response.status_code}")
            else:
                print("Failed to extract parameters MAY BE ACCOUNT IS ALREADY LOCKED")

        except Exception as e:
            print(f"An error occurred: {e}")
            import traceback
            traceback.print_exc()

