from PicImageSearch import SauceNAO,Network
from PicImageSearch.model import SauceNAOResponse
from pixivpy_async import *
from loguru import logger
import re
import traceback
import asyncio
import os
import math

from .dao import verifyDao,deleteDao
from .utils import config,setu_folder
from .normal_function import redownload_from_tencent

pixiv_on = config['pixiv']['on']
sauceNAO_on = config['sauceNAO']['on']
sauceNAO_proxy_on = config['sauceNAO']['proxy_on']
pixiv_proxy_on = config['pixiv']['proxy_on']
sauceNAO_sleep = math.ceil(30/config['sauceNAO']['limit'])

#获取图片pixiv_id
async def get_pixiv_id(url):
    """
    url: 待搜索图片url
    从sauceNAO上搜索图片，返回P站ID和文件名
    """
    try:
        if sauceNAO_on:
            pixiv_id,index_name,sauceNAO_proxy = 0,'',None
            if sauceNAO_proxy_on:
                sauceNAO_proxy = config['proxies']['proxy']
            async with Network(proxies = sauceNAO_proxy) as client:
                saucenao = SauceNAO(api_key=config['sauceNAO']['token'], client=client, minsim = 60)
                if url[:4] == 'http':               # 网络url
                    res = await saucenao.search(url=url)
                else:                               # 本地文件
                    file = open(url, "rb")
                    res = await saucenao.search(file=file)
                if res:
                    print(res.raw)
                    for raw in res.raw:
                        if raw.pixiv_id:
                            pixiv_id = raw.pixiv_id     
                            index_name = raw.index_name
                            break
                    return pixiv_id,index_name
                else:
                    return 0,''
        else:
            return 0,''
    except:
        logger.error(traceback.format_exc())
        return 0,''
    
#获取图片pixiv_tag和原图urla
async def get_pixiv_tag_url(pixiv_id,page):
    """
    pixiv_id: P站作品ID
    page: P站作品页码
    返回TAG,中文TAG，是否R18，P站大图链接
    """
    try:
        if pixiv_on:
            if pixiv_proxy_on:
                pixiv_proxy = config['proxies']['proxy']
            else:
                pixiv_proxy = None
            async with PixivClient(proxy = pixiv_proxy) as client:
                aapi = AppPixivAPI(client=client,proxy = pixiv_proxy)
                if config['pixiv']['refresh_token']:
                    await aapi.login(refresh_token=config['pixiv']['refresh_token'])
                elif config['pixiv']['username'] and config['pixiv']['password']:
                    await aapi.login(config['pixiv']['username'], config['pixiv']['password'])
                aapi.set_accept_language('zh-cn')
                json_result = await aapi.illust_detail(pixiv_id)
                if not hasattr(json_result.illust,'title'):
                    return '','',0,''
                page_count = json_result.illust.page_count
                illust = json_result.illust.tags
                if not illust:
                    return '','',0,''
                pixiv_tag,pixiv_tag_t,pixiv_url,r18='','','',0
                if illust[0]['name'] == 'R-18':
                    r18 = 1
                for i in illust:
                    pixiv_tag = pixiv_tag.strip()+ " "+ str(i['name']).strip('R-18')
                    pixiv_tag_t = pixiv_tag_t.strip() + " "+ str(i['translated_name']).strip('None') #拼接字符串 处理带引号sql
                pixiv_tag = pixiv_tag.strip()
                pixiv_tag_t = pixiv_tag_t.strip()
                if page_count == 1:
                    pixiv_url=json_result.illust.meta_single_page['original_image_url']
                else:
                    pixiv_url=json_result.illust.meta_pages[int(page)]['image_urls']['original']
                return pixiv_tag,pixiv_tag_t,r18,pixiv_url
        else:
            return '','',0,''
    except:
        logger.error(traceback.format_exc())
        return '','',0,''


#图片检测相似度，自动获取TAG
async def verify(id,url):
    """
    id:色图ID
    url:待搜索图片url
    返回：色图ID,审核状态,P站ID,待搜索图片url
    """
    try:
        pixiv_id,index_name = await get_pixiv_id(url)
        if not pixiv_id:
            verify = verifyDao().update_verify_stats(id,1)
        else:
            page = re.search(r'_p(\d+)',index_name,re.X)
            pixiv_tag,pixiv_tag_t,r18,pixiv_url = await get_pixiv_tag_url(pixiv_id,page.group(1))
            if not pixiv_tag:
                verify = verifyDao().update_verify_stats(id,1)
            else:
                verify = verifyDao().update_verify_info(id, pixiv_id ,pixiv_tag ,pixiv_tag_t ,r18 ,pixiv_url)
        return verify,pixiv_id
    except:
        logger.error(traceback.format_exc())
        verify = verifyDao().update_verify_stats(id,1)
        return 1,None
    
    
#从指定ID开始自动审核（获取TAG）
async def auto_verify(id):
    try:
        results = verifyDao().get_verify_list(id)
        id,success,failed,delete = 0,0,0,0
        for row in results:
            try:
                id = row[0] #参数初始化
                url= setu_folder+'/'+row[1]
                pixiv_tag,pixiv_tag_t,pixiv_url,r18='','','',0
                print(f'id='+ str(id))
                if not os.path.exists(os.path.abspath(url)):
                    msg = await redownload_from_tencent(id)
                    logger.info(msg)
                    if not os.path.exists(os.path.abspath(url)):
                        deleteDao().delete_image(id)
                        logger.info(f'{id}本地找不到文件，已自动删除')
                        delete += 1
                        continue
                pixiv_id,index_name = await get_pixiv_id(url)
                if not pixiv_id:
                    logger.info(f'id:{id}未通过自动审核,可能刚上传至P站或无法访问saucenao或token达到单日上限')
                    failed += 1
                    #time.sleep(1)
                else:
                    page = re.search(r'_p(\d+)',index_name,re.X)
                    if not page:
                        pagenum = 0
                    else:
                        pagenum = page.group(1)
                    pixiv_tag,pixiv_tag_t,r18,pixiv_url = await get_pixiv_tag_url(pixiv_id,pagenum)
                    if not pixiv_tag:
                        logger.info(f'id:{id}未通过自动审核,可能原画已被删除或无法访问P站API')
                        failed += 1
                        #time.sleep(1)
                    else:
                        verifyDao().update_verify_stats(id,0)
                        verifyDao().update_verify_info(id,pixiv_id,pixiv_tag,pixiv_tag_t,r18,pixiv_url)
                        logger.info(f'id:{id}通过自动审核,已自动为您获取原图PixivID:{pixiv_id}')
                        success += 1
                await asyncio.sleep(sauceNAO_sleep)
            except:
                logger.error(traceback.format_exc())
                pass
        return f"重新自动审核完成\n成功{success}张\n失败{failed}张\n删除{delete}张"
    except:
        logger.error(traceback.format_exc())