import asyncio
import os
import traceback
from collections import defaultdict, namedtuple
from turtle import down
from .utils import download,setu_folder,config
from .dao import loadImgDao
from .publicAPI import verify

verify_group = config['verify_group']

LoadImageState = namedtuple("LoadImageState", ['state','time','group_id', 'user_id', 'is_private', 'is_man'])
LoadImageProcess = defaultdict(lambda: LoadImageState(False, 0, None, None, False, 0))

async def start_load(state=True,group_id=None,user_id=None,is_private=False,is_man=0):
    LoadImageProcess[user_id] = LoadImageState(state, 20, group_id,user_id,is_private,is_man)
    while LoadImageProcess[user_id].time > 0 and LoadImageProcess[user_id].state:
        LoadImageProcess[user_id] = LoadImageProcess[user_id]._replace(time = LoadImageProcess[user_id].time - 0.5)
        await asyncio.sleep(0.5)
    return await quit_load(user_id)

async def quit_load(user_id):
    LoadImageProcess[user_id] = LoadImageProcess[user_id]._replace(state = False)
    return '已退出上传模式'
    
    
async def reset_load_time(user_id):
    LoadImageProcess[user_id] = LoadImageProcess[user_id]._replace(time = 20)
    return

async def load_image(bot,ev,is_man):
    try:
        tag = ""
        #threads1 = []
        threads2 = []
        tasks1 = []
        if ((str(ev).find("'file': {")+1)):    #文件
            tencent_url = ev['file']['url']
            url = ev['file']['name']
            user = str(ev['user_id'])
            result = loadImgDao().check_url(url)
            if not result:
                id = loadImgDao().load_image(url,user,tag,is_man,tencent_url)
                #threads1.append(MyThread(new_download,(img_url, os.path.join(setu_folder,setu_name)),verify.__name__))
                #tasks1.append(download(tencent_url, os.path.join(setu_folder,setu_name)))
                await download(tencent_url, os.path.join(setu_folder,url))
                await bot.send(ev, f'[CQ:image,file={tencent_url}]'+f'涩图收到了~id为{id}\n自定义TAG为{tag}\n稍后会自动从P站获取TAG\n删除请发送删除色图{id}')
                #threads2.append(MyThread(verify,(id,tencent_url),verify.__name__))
                verifynum,pixiv_id = await verify(id,tencent_url)
                await send_verify_result(bot,ev,id,pixiv_id,tencent_url,verifynum,is_man)
            else:
                await bot.send(ev, f'涩图已经存在了哦~id为{result[0]}')    
                        
        else:                               #图片
            for seg in ev.message:
                if seg.type == 'text':
                    tag=str(seg).strip()
                elif seg.type == 'image':
                    tencent_url = seg.data['url']
                    url = str(seg.data['file'])
                    user = str(ev['user_id'])
                    result = loadImgDao().check_url(url)
                    if not result:
                        id = loadImgDao().load_image(url,user,tag,is_man,tencent_url)
                        #threads1.append(MyThread(new_download,(img_url, os.path.join(setu_folder,setu_name)),verify.__name__))
                        #tasks1.append(download(tencent_url, os.path.join(setu_folder,setu_name)))
                        await download(tencent_url, os.path.join(setu_folder,url))
                        await bot.send(ev, f'[CQ:image,file={tencent_url}]'+f'涩图收到了~id为{id}\n自定义TAG为{tag}\n稍后会自动从P站获取TAG\n删除请发送删除色图{id}')
                        #threads2.append(MyThread(verify,(id,tencent_url),verify.__name__))
                        verifynum,pixiv_id = await verify(id,tencent_url)
                        await send_verify_result(bot,ev,id,pixiv_id,tencent_url,verifynum,is_man)
                    else:
                        await bot.send(ev, f'涩图已经存在了哦~id为{result[0]}')
        #await asyncio.gather(*tasks1)
        #if proxy_on:
        #    if len(threads2)>sauceNao_limit:
        #        await bot.send(ev,'您本次上传的数量超过了sauceNAO30秒允许的最大值，部分图可能无法成功获取tag,请联系审核组或等待凌晨4点自动审核哦~')
        #    for t in threads2:
        #        t.setDaemon(True)
        #        t.start()
        #    for t in threads2:
        #        t.join()
        #        id,verifynum,pixiv_id,img_url= t.getResult()
        #        txt =  await redownload_from_tencent(id)        #校验本地缺失文件
        #        if not verifynum:
        #            await bot.send(ev, f'id:{id}上传成功，自动审核通过\n已自动为您获取原图PixivID:{pixiv_id}\n'+f"发送'查看原图+ID'即可")
        #        else:
        #            await bot.send(ev, f'id:{id}上传成功，但没完全成功，请等待人工审核哦~[CQ:at,qq={str(user)}]')
        #            for ves in verifies:
        #                if_man_txt = '色图'
        #                if is_man:
        #                    if_man_txt = '男图'
        #                await bot.send_private_msg(self_id=ev.self_id, user_id=int(ves), message=f'有新的上传申请,id:{id}\n上传者:{user} 分区:{if_man_txt}'+f'[CQ:image,file={img_url}]')
        #else:
        #    await bot.send(ev, f'由于您未开启代理，无法自动获取色图信息')
    except Exception as e:
        traceback.print_exc()
        await bot.send(ev, f'wuwuwu~上传出现了问题~请联系维护者提交错误信息{e}')
        
async def send_verify_result(bot,ev,id,pixiv_id,tencent_url,verifynum,is_man):
    if not verifynum:
        await bot.send(ev, f'id:{id}上传成功，自动审核通过\n已自动为您获取原图PixivID:{pixiv_id}\n'+f"发送'查看原图+ID'即可")
    else:
        await bot.send(ev, f"id:{id}上传成功，但没完全成功，请等待人工审核哦~[CQ:at,qq={str(ev['user_id'])}]")
        for ves in verify_group:
            if_man_txt = '色图'
            if is_man:
                if_man_txt = '男图'
            await bot.send_private_msg(self_id=ev.self_id, user_id=int(ves), message=f"有新的上传申请,id:{id}\n上传者:{str(ev['user_id'])} 分区:{if_man_txt}\n[CQ:image,file={tencent_url}]")
            
