from typing import AsyncIterable
from pixivpy3 import *
from PicImageSearch import SauceNAO
import os
import json
import time
import requests
import pymysql
import time
from loguru import logger

with open('C:/Users/Administrator/Desktop/hoshino_xcw/XCW/HoShino/hoshino/modules/setu/config.json') as json_data_file:
    config = json.load(json_data_file)





def get_pixiv_id(url):
    pixiv_id = 0
    saucenao = SauceNAO(api_key=api_key,**_REQUESTS_KWARGS)
    res = saucenao.search(url)
    pixiv_id = res.raw[0].pixiv_id
    print(pixiv_id)
    similarity = res.raw[0].similarity
    if similarity < 60 or pixiv_id == '' or not pixiv_id:
        print(res.raw[0].similarity)
        pixiv_id = 0
    return pixiv_id,similarity
def get_pixiv_tag(pixiv_id):
    try:
        api = AppPixivAPI()
        api.set_accept_language('zh-cn')
        api.auth(refresh_token=refresh_token)
# get origin url
        json_result = api.illust_detail(pixiv_id)
        illust = json_result.illust.tags
        r18 = 0
        pixiv_tag = ''
        pixiv_tag_t = ''
        if illust[0]['name'] == 'R-18':
            r18 = 1
        for i in illust:
            pixiv_tag = pixiv_tag.strip()+ " "+ str(i['name']).strip('R-18').replace("'","\\'")
            pixiv_tag_t = pixiv_tag_t.strip() + " "+ str(i['translated_name']).strip('None').replace("'","\\'") #拼接字符串 处理带引号sql
        pixiv_tag = pixiv_tag.strip()
        pixiv_tag_t = pixiv_tag_t.strip()
        return pixiv_tag,pixiv_tag_t,r18
    except Exception as e:
        print("yichang1",e)
        return '','',0
