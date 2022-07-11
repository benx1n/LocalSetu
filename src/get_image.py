import os
import traceback
from hoshino import R

from .dao import getImgDao

setu_folder = R.get('img/setu/').path

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
           return '该群友xp不存在~~~',None
       
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
            return "该图正在等待审核，暂不支持查看~",None
        if not tag:
            tag = f'当前TAG为空，您可以发送修改TAG{id}进行编辑~'
        else:
            tag = f'自定义TAG:{str(tag)}'
        if pixiv_id :
            pixiv_url = "https://pixiv.net/i/"+ str(pixiv_id)
            msg = f'\n涩图ID:{id} 来源[CQ:at,qq={str(user)}]'+ f'\n{str(tag)}'+f'\nPixivTAG:{pixiv_tag}' +f'\n{pixiv_url}' +f'\n支持ID、来源、TAG模糊查询哦~'
            return msg,url
        else:
            msg = f'\n涩图ID:{id} 来源[CQ:at,qq={str(user)}]'+ f'\n{str(tag)}'+f'\nPixivTAG:{pixiv_tag}' +f'\n支持ID、来源、TAG模糊查询哦~'
            return msg,url
    except:
        traceback.print_exc()
        return 'wuwuwu~出了点问题',None