from typing import AsyncIterable
from pixivpy3 import *
import os
import json
import time
import requests
import pymysql
import time
from loguru import logger
from PicImageSearch import AsyncSauceNAO, NetWork
import asyncio

with open('C:/Users/Administrator/Desktop/hoshino_xcw/XCW/HoShino/hoshino/modules/setu/config.json') as json_data_file:
    config = json.load(json_data_file)

host = config['mysql']['host']
user=config['mysql']['user']
password=config['mysql']['password']
database=config['mysql']['database']
api_key=config['api']['sauceNAO']
refresh_token=config['api']['refresh_token']

_REQUESTS_KWARGS = {
        'proxies': {
          'https': 'http://127.0.0.1:7890',
      }
    }
setu_folder = "C:/Users/Administrator/Desktop/hoshino_xcw/XCW/res/img/setu"
conn = pymysql.connect(host=host,user=user,password=password,database=database)
cursor = conn.cursor()
async def get_pixiv_id(url):
    start = time.time()
    pixiv_id = 0
    async with NetWork(proxy='http://127.0.0.1:7890') as client:
        try:
            saucenao = AsyncSauceNAO(client=client,api_key=api_key)
            res = await saucenao.search(str(url))
        except Exception as e:
            print("wrong",e)
        pixiv_id = res.raw[0].pixiv_id
        print(res.raw[0].raw)
        print(res.raw[1].raw)
        print(res.raw[2].raw)
        #print(pixiv_id)
        #await asyncio.sleep(1)
        pixiv_tag,pixiv_tag_t,r18=get_pixiv_tag(pixiv_id)
        #if res.raw[0].similarity < 60 or pixiv_id == '' or not pixiv_id:
        #    print(res.raw[0].similarity)
        #    pixiv_id = 0
       # pixiv_tag,pixiv_tag_t,r18= get_pixiv_tag(pixiv_id)
        #print("已获取到pixiv_tag"+pixiv_tag_t)
        print("usetime:%f s"%(time.time()-start))
        #return id,pixiv_id,pixiv_tag,pixiv_tag_t,r18



def get_pixiv_tag(pixiv_id):
    try:
        api = AppPixivAPI()
        api.set_accept_language('zh-cn')
        api.auth(refresh_token=refresh_token)
# get origin url
        json_result = api.illust_detail(pixiv_id)
        print(json_result)
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

async def main():
    sql="SELECT id,url FROM bot.localsetu where pixiv_id = 0 limit 1"
    #sql="SELECT id,url FROM bot.localsetu where id = 759 or id =760 or id=761 ORDER BY id limit 1"
    cursor.execute(sql)
    results = cursor.fetchall()
    id = 0
    tasks=[]
    start = time.time()
    for row in results:
        id = row[0] #参数初始化
        #url= setu_folder+'/'+row[1]
        url= 'https://pixiv.cat/92252996.jpg'
        pixiv_tag=''
        pixiv_tag_t=''
        r18=0
        pixiv_id = tasks.append(get_pixiv_id(url))
    await asyncio.gather(*tasks)
    print("usetime:%f s"%(time.time()-start))
    
    
'''            print(pixiv_id)
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
        conn.commit()'''

if __name__ == "__main__":
    asyncio.run(main())
