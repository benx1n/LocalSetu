import os
import traceback
from PIL import Image
from loguru import logger
from .dao import normalDao
from hoshino.typing import MessageSegment
from .utils import setu_folder,download,image_random_one_pixel,image2MD5

async def redownload_from_tencent(id):
    try:
        result = normalDao().get_tecent_url(id)
        if not result:
            return f'id{id}不存在~~~'
        if not result[1]:
            return f'id{id}的腾讯服务器url不存在~~~'
        local_url = os.path.join(setu_folder,result[0])
        if not os.path.exists(os.path.abspath(local_url)):
            try:
                await download(result[1], local_url)
                msg = f'id{id}下载成功'
            except:
                msg = f'id{id}下载失败，可能是腾讯服务器url过期了~'
        else:
            msg = f'id{id}本地文件已存在哦~'
        return msg
    except:
        logger.error(traceback.format_exc())

async def update_tag(tag,id):
    normalDao().update_tag(tag,id)
    
async def anti_image(id):
    try:
        results = normalDao().get_anti_url(id)
        if not results:
           return '该图片不存在~~~'
        for row in results:
            name = row[0]
            url = os.path.join(setu_folder,row[0])
            anti_url = row[1]
        if anti_url:
            os.remove(os.path.join(setu_folder,anti_url))
            #await bot.send(ev, f'原反和谐文件已删除\\I I/')
        tem_name_url = os.path.join(setu_folder,"Anti_harmony_"+name) #临时文件，因为后面计算MD5需要的是文件而不是图片
        img = Image.open(url)
        img = await image_random_one_pixel(img)
        img.save(tem_name_url,'jpeg',quality=75)
        new_MD5 = await image2MD5(tem_name_url)   #格式是xx.image
        new_url = os.path.join(setu_folder,new_MD5)
        os.rename(tem_name_url,new_url)
        normalDao().update_anti_url(new_MD5,id)
        return str(MessageSegment.image(f'file:///{os.path.abspath(new_url)}')) + '\n反和谐成功~'
    except:
        logger.error(traceback.format_exc())
        return '反和谐失败了呜呜呜~'
    
async def anti_image_temporary(pixiv_id,pixiv_proxy_url):
    """临时反和谐"""
    try:
        Anti_harmony_url=setu_folder+"/Anti_harmony_777"
        await download(pixiv_proxy_url, Anti_harmony_url)   
        img = Image.open(Anti_harmony_url)
        img = await image_random_one_pixel(img)
        Anti_harmony_url = Anti_harmony_url + '8'
        img.save(Anti_harmony_url,'PNG',quality=75)
        return str(MessageSegment.image(f'file:///{os.path.abspath(Anti_harmony_url)}'))+f'\n本图片进过反和谐，若有原图需要请从反代链接下载'+ f'\n原图链接：https://pixiv.net/i/{pixiv_id}' + f'\n反代链接:{pixiv_proxy_url}'
    except:
        logger.error(traceback.format_exc())