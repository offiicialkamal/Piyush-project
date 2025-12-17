from core import batch_runner
from queue import Queue



result_container = Queue()

cookies_batch = [{"datr=OZ4oaaPMapVsAMgQ-kctLHAf; fr=1pXZrWFE4HqVWV2wj.AWejfeSTh--N3PulYdY5Tpt94ymCXqn_KwOcD9Gak4vn1geUPAY.BpPvJN..AAA.0.0.BpPvJN.AWfhqEC1Jxqa2Sc0mxTIO2Y1csM; sb=OZ4oaetTZUNpwQtVht7HwxCu; wd=588x479; dpr=1.6800000667572021; locale=en_US; ps_l=1; ps_n=1; c_user=61558074221758; xs=41%3AwPxC4m9Aw-KdHw%3A2%3A1765119401%3A-1%3A-1%3A%3AAcySD8XTcwi2Vxf7cA3VX--_s5yQSgMBTdkjY7CBhQ; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1765732966716%2C%22v%22%3A1%7D": ["Mozilla/5.0 (Windows NT 8.3.1; Win64; x64) KHTML/like Gecko Opera/94.362.3411.7 Safari/537.36"]}]
post_link = "https://www.facebook.com/share/1AkJY1hLLP/"
comment = "This is hacking star"
comment_per_acc = 1


cookie = cookies_batch[0]

print(type(list(cookie.keys())[0]))





t = batch_runner(cookies_batch, post_link,  comment, comment_per_acc, result_container)
t.start()
