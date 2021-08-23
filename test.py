from PicImageSearch import SauceNAO
_REQUESTS_KWARGS = {
    'proxies': {
      'https': 'http://127.0.0.1:7890',
      }
    }
saucenao = SauceNAO(api_key='a36c566e679af0526da9399c3c6f1865d7e1739e',**_REQUESTS_KWARGS)
res = saucenao.search('C:/Users/Administrator/Desktop/hoshino_xcw/XCW/res/img/setu/ae3f7f592ff04c1ed99158e593133b37.image')
print(res.raw[0].raw)