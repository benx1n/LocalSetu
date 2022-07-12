import asyncio
import os
import traceback
from loguru import logger
from collections import defaultdict, namedtuple
from hoshino.typing import MessageSegment
from .utils import download,setu_folder,config
from .dao import verifyDao,deleteDao
from .publicAPI import verify
from .normal_function import redownload_from_tencent

verify_group = config['verify_group']

VerifyImageState = namedtuple("LoadImageState", ['state','sql_state','verify_type','image_info','time'])
VerifyImageProcess = defaultdict(lambda: VerifyImageState(False, False, 1, None, 0))

async def start_verify(bot,ev,user_id, verify_type ,state=True,sql_state=False,image_info=None,time=20):
    try:
        VerifyImageProcess[user_id] = VerifyImageState(state, sql_state, verify_type,image_info, time)
        while VerifyImageProcess[user_id].time > 0 and VerifyImageProcess[user_id].state:
            if not VerifyImageProcess[user_id].sql_state:                      #没有待审核图则重新拿一张并发送
                results = verifyDao().get_verify_info(verify_type)
                if not results:
                    return '好耶，当前没有要审核的图~'
                VerifyImageProcess[user_id] = VerifyImageProcess[user_id]._replace(image_info = results)
                man_text = '色图'
                if results[4]:
                    man_text = '男图'
                await bot.send(ev, '当前审核的图片为'+str(MessageSegment.image(f'file:///{os.path.abspath(os.path.join(setu_folder,results[0]))}'))+f'ID：{results[3]}\n来源为[CQ:at,qq={str(results[1])}]\n类型为:{man_text}\n上传时间:{results[2]}')
                VerifyImageProcess[user_id] = VerifyImageProcess[user_id]._replace(sql_state = True)

            VerifyImageProcess[user_id] = VerifyImageProcess[user_id]._replace(time = VerifyImageProcess[user_id].time - 0.5)  
            await asyncio.sleep(0.5)
        return await quit_verify(user_id)
    except:
        logger.error(traceback.format_exc())

async def quit_verify(user_id):
    try:
        VerifyImageProcess[user_id] = VerifyImageProcess[user_id]._replace(state = False)
        return '20秒到了，已退出审核模式'
    except:
        logger.error(traceback.format_exc())
    
async def reset_verify_time(user_id):
    try:
        VerifyImageProcess[user_id] = VerifyImageProcess[user_id]._replace(time = 20)
        return
    except:
        logger.error(traceback.format_exc())

async def update_verify_state(bot,ev,user_id,is_delete):
    try:
        if is_delete:               #删除
            deleteDao().delete_image(VerifyImageProcess[user_id].image_info[3])
            await bot.send(ev, 'OvO~不合格的涩图删掉了~')
        else:                       #保留
            verifyDao().update_verify_stats(VerifyImageProcess[user_id].image_info[3],0)
            await bot.send(ev, '当前图片审核通过'+str(MessageSegment.image(f'file:///{os.path.abspath(os.path.join(setu_folder,VerifyImageProcess[user_id].image_info[0]))}'))+f'id为{VerifyImageProcess[user_id].image_info[3]}')
        await reset_verify_time(user_id)
        VerifyImageProcess[user_id] = VerifyImageProcess[user_id]._replace(sql_state = False)
    except:
        logger.error(traceback.format_exc())
    