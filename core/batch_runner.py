from .single_runner import run_single
import threading
import time

class batch_runner(threading.Thread):
    def __init__(self, cookies_batch, post_link, comment, comment_per_acc, options, result_container):
        super().__init__()
        self.__cookies_batch = cookies_batch
        self.__post_link = post_link
        self.__comment = comment
        self.__comment_per_acc = comment_per_acc
        self.result_container = result_container
        self.__options = options

    def run(self):
        for cookie in self.__cookies_batch:
            t = run_single(cookie, self.__post_link, self.__comment, self.__comment_per_acc, self.__options, self.result_container)
            t.start()
            time.sleep(1/100)
            ## No join start the therads parlelly


