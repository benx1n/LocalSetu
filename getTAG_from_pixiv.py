from pixivpy3 import *
from PicImageSearch import SauceNAO

def get_tag(url):
    pixiv_id = 0
    _REQUESTS_KWARGS = {
    'proxies': {
      'https': 'http://127.0.0.1:7890',
      }
    }
    saucenao = SauceNAO(api_key='a36c566e679af0526da9399c3c6f1865d7e1739e',**_REQUESTS_KWARGS)
    res = saucenao.search(url)
    print(res.raw[0].pixiv_id)
    pixiv_id = res.raw[0].pixiv_id

    api = AppPixivAPI()
    api.set_accept_language('zh-cn')
    api.auth(refresh_token='-5YGz043uSWJpAenikubPJmHYY7UAhMtgQSeKv6EY2A')

# get origin url
    json_result = api.illust_detail(pixiv_id)
    illust = json_result.illust.tags
    list = ''
    for i in illust:
        list = list + str(i['translated_name']) + " "
    print(list)

if __name__ == "__main__":
    get_tag('https://gchat.qpic.cn/gchatpic_new/990345019/574432871-2551012026-FED07059E919DEEEB01D3A351E342DA4/0?term=3')