from main import commenter


class batch_runner:
    def __init__(self, cookies_batch, post_link, comment, comment_per_acc):
        self.__cookies_batch = cookies_batch
        self.__post_link = post_link
        self.__comment = comment
        self.__comment_per_acc = comment_per_acc

    def run(self):
        for cookie in self.__cookies_batch:
            t = commenter(cookie, self.post_link, self.__comment, self.__comment_per_acc)
            t.start()
            ## No join start the therads parlelly

