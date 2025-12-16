from .single_runner import run_single


class batch_runner:
    def __init__(self, cookies_batch, post_link, comment, comment_per_acc, result_container):
        self.__cookies_batch = cookies_batch
        self.__post_link = post_link
        self.__comment = comment
        self.result_container = result_container
        self.__comment_per_acc = comment_per_acc

    def run(self):
        for cookie in self.__cookies_batch:
            t = commenter(cookie, self.post_link, self.__comment, self.__comment_per_acc, self.result_container)
            t.start()
            ## No join start the therads parlelly

