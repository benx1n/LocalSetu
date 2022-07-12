import os
import traceback
import re


from .utils import config,download,setu_folder
from .dao import getImgDao
from .publicAPI import get_pixiv_id,get_pixiv_tag_url

pximgUrl = config['pixiv']['pximgUrl']

async def get_local_image(search_tag, user, search_type=0, is_man= 0):
    """
    search_tag: 匹配字段
    user: 查找用户
    seach_type: 查找方式: 0:全随机, 1:@指定人, 2:TAG/ID
    is_man: 0:色图, 1:男图
    """
    try:
        if search_type==0:                                                             #全随机
            result = getImgDao().get_local_image_random(is_man)
        elif search_type==1:                                                             #@群友
            result = getImgDao().get_local_image_user(is_man, user)
        elif search_type==2:                                                              #带TAG/ID
            if search_tag.isdigit():                                                     #id
                result = getImgDao().get_local_image_ID(is_man,search_tag)
            else:                                                                       #tag
                search_tag = '%'+search_tag+'%'
                result = getImgDao().get_local_image_tag(is_man,search_tag)
        else:
            result = None
        
        if not result:
           return '该群友xp不存在~~~',None,None
       
        id = result[0]
        url=os.path.join(setu_folder,result[1])
        anti_url = os.path.join(setu_folder,result[2])
        user = result[3]
        date = result[4]
        tag = result[5]
        pixiv_tag = result[6]
        pixiv_id = result[7]
        verify = result[9]
        if result[2]:
            url = anti_url
        if verify:
            return "该图正在等待审核，暂不支持查看~",None,None
        if not tag:
            tag = f'当前TAG为空，您可以发送修改TAG{id}进行编辑~'
        else:
            tag = f'自定义TAG:{str(tag)}'
        if pixiv_id :
            pixiv_url = "https://pixiv.net/i/"+ str(pixiv_id)
            msg = f'涩图ID:{id} 来源[CQ:at,qq={str(user)}]'+ f'\n{str(tag)}'+f'\nPixivTAG:{pixiv_tag}' +f'\n{pixiv_url}' +f'\n支持ID、来源、TAG模糊查询哦~'
            return msg,url,id
        else:
            msg = f'涩图ID:{id} 来源[CQ:at,qq={str(user)}]'+ f'\n{str(tag)}'+f'\nPixivTAG:{pixiv_tag}' +f'\n支持ID、来源、TAG模糊查询哦~'
            return msg,url,id
    except:
        traceback.print_exc()
        return 'wuwuwu~出了点问题',None,None
    
async def get_original_image(id,bot,ev):
    try:
        results = getImgDao().get_original_image(id)
        if not results:
            return "请检查id是否正确~",None
        elif results[1]:
            return "该涩图正在等待审核，暂不支持查看~", None
        pixiv_url = results[0]
        pixiv_name = results[2]
        pixiv_id = results[3]
        if not pixiv_name:
            await bot.send(ev, '本地没有找到记录，正在尝试获取原画')
            pixiv_id,index_name= await get_pixiv_id(os.path.join(setu_folder,results[4]))
            if not pixiv_id:
                return '获取失败了~',None
            else:
                page = re.search(r'_p(\d+)',index_name,re.X)
                pixiv_tag,pixiv_tag_t,r18,pixiv_url = await get_pixiv_tag_url(pixiv_id,page.group(1))
                if not pixiv_tag:
                    return '无法获取原画，该原画可能已被删除',None
                else:
                    if pximgUrl:
                        pixiv_proxy_url = re.sub(r"^https://(.*?)/",pximgUrl,pixiv_url)
                    pixiv_name = os.path.split(pixiv_proxy_url)[1]
                    await download(pixiv_proxy_url,os.path.join(setu_folder,pixiv_name))
                    getImgDao().update_original_image(pixiv_id,pixiv_tag,pixiv_tag_t,r18,pixiv_proxy_url,pixiv_name,id)
        url=os.path.join(setu_folder,pixiv_name)
        pixiv_proxy_url = re.sub(r"^https://(.*?)/",pximgUrl,pixiv_url)
        msg = f'原图链接：https://pixiv.net/i/{pixiv_id}' + f'\n反代链接:{pixiv_proxy_url}'
        return msg,url
    except:
        traceback.print_exc()
        return 'wuwuwu~出了点问题',None