from pixivpy3 import *
from PicImageSearch import SauceNAO
import os
import json
import requests
import pymysql
import time
from loguru import logger

with open('./config.json') as json_data_file:
    config = json.load(json_data_file)

host = config['mysql']['host']
user=config['mysql']['user']
password=config['mysql']['password']
database=config['mysql']['database']
api_key=config['api']['sauceNAO']
refresh_token=config['api']['refresh_token']

setu_folder = "C:/Users/Administrator/Desktop/hoshino_xcw/XCW/res/img/setu"
conn = pymysql.connect(host=host,user=user,password=password,database=database)
cursor = conn.cursor()

def get_pixiv_id(url):
    pixiv_id = 0
    _REQUESTS_KWARGS = {
    'proxies': {
      'https': 'http://127.0.0.1:7890',
      }
    }
    saucenao = SauceNAO(db = 5,api_key=api_key,**_REQUESTS_KWARGS)
    res = saucenao.search(url)
    pixiv_id = res.raw[0].pixiv_id
    if res.raw[0].similarity < 60 or pixiv_id == '' or not pixiv_id:
        print(res.raw[0].similarity)
        pixiv_id = 0
    return pixiv_id


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

if __name__ == "__main__":
    #sql="SELECT id,url FROM bot.localsetu where pixiv_id is NULL limit 10"
    sql="SELECT id,url FROM bot.localsetu ORDER BY id limit 1000"
    cursor.execute(sql)
    results = cursor.fetchall()
    url=''
    id = 0
    for row in results:
        id = row[0] #参数初始化
        url= setu_folder+'/'+row[1]
        pixiv_tag=''
        pixiv_tag_t=''
        r18=0
        print(id)
        try:
            pixiv_id= get_pixiv_id(url)
            print(pixiv_id)
            try:
                pixiv_tag,pixiv_tag_t,r18=get_pixiv_tag(pixiv_id)
            except Exception as e:
                print("yichang2",e)
                continue
            pixiv_tag_t = pixiv_tag_t.strip('None')
            print(pixiv_tag)
            print(pixiv_tag_t)
        except Exception as e:
            print("yichang3",e)
            continue
        sql="update localsetu set pixiv_id = %s , pixiv_tag = \'%s\' , pixiv_tag_t = \'%s\' , r18 = %s where id = %s"%(pixiv_id,pixiv_tag,pixiv_tag_t,r18,id)
        cursor.execute(sql)
        conn.commit()
