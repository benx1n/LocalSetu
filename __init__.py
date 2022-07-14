import os
import re
import traceback
from pathlib import Path
from loguru import logger


from nonebot.exceptions import CQHttpError
import hoshino
from hoshino import R, Service, priv, get_bot
from hoshino.util import FreqLimiter, DailyNumberLimiter
from hoshino.typing import CQEvent, MessageSegment
from nonebot import NoticeSession, on_command
from .src.utils import config
from .src.get_image import get_local_image,get_original_image
from .src.load_image import start_load, quit_load, reset_load_time, load_image, LoadImageProcess
from .src.delete_image import delete_image
from .src.normal_function import update_tag,anti_image,anti_image_temporary,redownload_from_tencent
from .src.verify_image import start_verify,quit_verify,reset_verify_time,update_verify_state,VerifyImageProcess
from .src.publicAPI import get_pixiv_id,get_pixiv_tag_url,auto_verify
from .src.dao import verifyDao,normalDao,update_db

dir_path = Path(__file__).parent
verify_group = config['verify_group']
pximgUrl = config['pixiv']['pximgUrl']
setu_folder = R.get('img/setu/').path
_max = 100
EXCEED_NOTICE = f'您今天已经冲过{_max}次了，请明早5点后再来！'
_nlmt = DailyNumberLimiter(_max)
_flmt = FreqLimiter(5)


SETU_help="""LocalSetu涩图帮助指南：
- -kkqyxp/kkntxp[keyword]：随机发送色图/男同图，其中keyword为可选参数，支持ID、@上传者、TAG模糊查询
- -上传色/男图[TAG][图片][TAG][图片][TAG][图片]，其中TAG为可选参数，可跟多张图片
- -上传色/男图[无参数]：进入上传模式，该模式下用户发送的所有图片均视为上传，发送[退出上传]或无操作20秒后自动退出
- -查看原图[ID]：可用于保存原画画质的色图
- -删除色图[ID]：删除指定ID色图，非审核组成员仅可删除本人上传的色图，他人色图将会推送至审核组
- -修改TAG[ID][TAG]：修改指定ID的自定义TAG
- -反和谐[ID]：色图被TX屏蔽时使用该指令，进行一次反和谐，后续发送色图均使用反和谐后文件
- -PID/pid[ID]:通过pixivID查看P站原图
- -上传统计：让我康康谁才是LSP！
- -[BETA]sql：批量涩图，sql+数量+空格+条件，如sql10 id>1000，条件可参考sql表结构
- -仓库地址：https://github.com/pcrbot/LocalSetu 有问题欢迎提issue
=======审核组用户有以下指令：
= =审核色图[上传][删除]：进入审核模式，每次发送待审核的色图，使用指令[保留][删除]后自动发送下一张，发送[退出审核]或20秒无操作自动退出
= =快速审核[ID]：快速通过指定ID的申请（默认保留）
= =重新自动审核/重新获取TAG[起始ID]：重新审核/获取TAG，适用于首次上传由于SauceNAO接口限制而导致的批量自动审核失败
"""


sv = Service('LocalSetu', manage_priv=priv.SUPERUSER, enable_on_default=True, help_= SETU_help)


@sv.on_fullmatch(('色图帮助','setuhelp','色图帮助','setu帮助','LocalSetu'))
async def verify_setu_new(bot, ev: CQEvent):
    await bot.send(ev,SETU_help)

@sv.on_prefix(('kkqyxp','看看群友xp','看看群友性癖','kkntxp','看看男同xp','看看男同性癖'))
async def send_local_setu(bot, ev):
    try:
        qqid = ev['user_id']
        if not _nlmt.check(qqid):
            await bot.send(ev, EXCEED_NOTICE, at_sender=True)
            return
        if not _flmt.check(qqid):
            await bot.send(ev, '您冲得太快了，请稍候再冲', at_sender=True)
            return
        _flmt.start_cd(qqid)
        _nlmt.increase(qqid) 
        searchtag = str(ev.message).strip()
        if not searchtag or searchtag=="":
            search_type= 0                               #随机
        elif ev.message[0].type == 'at':
            search_type = 1                              #@指定人
            qqid = int(ev.message[0].data['qq'])
        else:
            search_type = 2                              #TAG/ID
        if ev['prefix'] == ('kkntxp'or '看看男同xp' or '看看男同性癖'):
            is_man = 1
        else:
            is_man = 0
        msg,url,id = await get_local_image(searchtag,qqid,search_type,is_man)
        if url:
            await bot.send(ev, f"{str(MessageSegment.image(f'file:///{os.path.abspath(url)}'))}\n{msg}")
        else:
            await bot.send(ev, msg)
    except CQHttpError:
        logger.warning(traceback.format_exc())
        sv.logger.error(f"发送图片{id}失败")
        try:
            await bot.send(ev, 'T T涩图不知道为什么发不出去勒...正在尝试反和谐后发送')
            anti_msg = await anti_image(id)
            await bot.send(ev, anti_msg)
        except:
            logger.warning(traceback.format_exc())
            pass

@sv.on_prefix(('查看原图','看看原图','看看大图','查看大图','查看原画'))
async def get_original_setu(bot, ev: CQEvent):
    id = str(ev.message).strip()
    if not id or not id.isdigit():
        await bot.send(ev, "请在后面加上要查看的涩图序号~")
        return
    try:
        msg,url,pixiv_id,pixiv_proxy_url = await get_original_image(id,bot,ev)
        if url:
            await bot.send(ev, f"{str(MessageSegment.image(f'file:///{os.path.abspath(url)}'))}\n{msg}")
        else:
            await bot.send(ev, msg)
    except CQHttpError:
        logger.error(traceback.format_exc())
        sv.logger.warning(f"发送图片{id}失败")
        try:
            await bot.send(ev, 'T T涩图不知道为什么发不出去勒...正在尝试反和谐后发送')
            anti_msg = await anti_image_temporary(pixiv_id,pixiv_proxy_url)
            await bot.send(ev, anti_msg)
        except:
            logger.warning(traceback.format_exc())
            pass
        
@sv.on_prefix(('上传色图','上传男图'))
async def start_load_image(bot, ev:CQEvent):
    try:
        is_man = 0
        if ev['prefix'] == '上传男图': 
            is_man = 1
        if not str(ev.message).strip():
            user_id=ev['user_id']
            if LoadImageProcess[user_id].state:
                await bot.send(ev, '您已经在上传模式中了哦~')
                return
            await bot.send(ev, '发涩图发涩图~开启收图模式~')
            if ev['message_type']== 'private':
                group_id=None
                is_private = True
            else:
                group_id=ev['group_id']
                is_private = False
            msg = await start_load(group_id=group_id,is_private=is_private,user_id=user_id,is_man=is_man)
            await bot.send(ev,msg)
            return
        await load_image(bot,ev,is_man)     #不进入上传模式，直接上传
    except:
        logger.error(traceback.format_exc())
        await quit_load(user_id)
        await bot.send(ev, 'wuwuwu~上传失败了~')
        
#监听:消息类型的图片
@sv.on_message()
async def is_load_image(bot, ev:CQEvent):
    try:
        user_id=ev['user_id']
        if not LoadImageProcess[user_id].state:       #是否处于上传模式
            return
        if not LoadImageProcess[user_id].is_private :     #是否群聊
            if 'group_id' in ev.keys() and LoadImageProcess[user_id].group_id != ev['group_id']:     #开启色图模式的和发图的是不是同一个群
                return
        else:                                           #私聊
            if ev['message_type'] != 'private':
                return
        if not (str(ev.message).find("[CQ:image")+1):  #判断收到的信息是否为图片，不是就退出
            return
        await reset_load_time(user_id)
        await load_image(bot,ev,LoadImageProcess[user_id].is_man)
    except:
        logger.error(traceback.format_exc())
    
#监听:文件类型的图片  
@sv.on_notice()
async def is_load_file(session: NoticeSession):
    try:
        ev = session.event
        if not 'user_id' in ev:
            return
        user_id=ev['user_id']
        print(user_id)
        if not LoadImageProcess[user_id].state:       #是否处于上传模式
            return
        if not ((str(ev).find("'file': {")+1)):  #判断收到的信息是否为文件，不是就退出
            return
        bot = get_bot()
        await reset_load_time(user_id)
        await load_image(bot,ev,LoadImageProcess[user_id].is_man)
    except:
        logger.error(traceback.format_exc())
  
@sv.on_prefix(('删除涩图', '删除色图','删除男图'))
async def del_image(bot, ev: CQEvent):
    try:
        id = str(ev.message).strip()
        user = ev['user_id']
        if not id or not id.isdigit():
            await bot.send(ev, "请在后面加上要删除的涩图序号~")
            return
        msg = await delete_image(id,user,bot,ev)
        await bot.send(ev,msg)
    except:
        logger.error(traceback.format_exc())

@sv.on_prefix(('修改TAG','修改tag'))
async def modify_tag(bot, ev: CQEvent):
    if not str(ev.message).strip():
        await bot.send(ev, '请在指令后添加ID和TAG哦~以空格区分')
        return
    try:
        id,tag=str(ev.message).split(' ', 1 )
        await update_tag(tag,id)
        await bot.send(ev, f'涩图{id}的TAG已更新为{tag}')
    except:
        logger.error(traceback.format_exc())
        await bot.send(ev, '请在指令后添加ID和TAG哦~以空格区分')

@sv.on_prefix(('反和谐'))
async def Anti_harmony(bot, ev: CQEvent):
    try:
        id = str(ev.message).strip()
        if not id or not id.isdigit():
            await bot.send(ev, '请输入要反和谐的图片ID')
        else:
            msg = await anti_image(id)
            await bot.send(ev, msg)
    except:
        logger.error(traceback.format_exc())
    
@sv.on_fullmatch(('审核色图上传','审核色图删除'))
async def verify_setu(bot, ev: CQEvent):
    try:
        user_id = int(ev["user_id"])
        if user_id not in verify_group:
            await bot.send(ev, '你谁啊你，不是管理员没资格审核色图哦~')
            return
        if VerifyImageProcess[user_id].state == True:
            await bot.send(ev, '您已经在审核模式中了哦~')
            return
        if ev['prefix'] == '审核色图上传':
            verifynum = 1
        elif ev['prefix'] == '审核色图删除':
            verifynum = 2
        msg = await start_verify(bot,ev,int(ev["user_id"]),verifynum)
        await bot.send(ev, msg)
    except:
        logger.error(traceback.format_exc())

@sv.on_fullmatch(('保留','删除','退出审核','退出上传'))
async def verify_complete(bot, ev: CQEvent):
    try:
        user_id = int(ev["user_id"])
        if ev['prefix'] == '退出上传':
            LoadImageProcess[user_id] = LoadImageProcess[user_id]._replace(state = False)
        if not VerifyImageProcess[user_id].state or user_id not in verify_group:
            return
        if ev['prefix'] == '保留':
            await update_verify_state(bot,ev,user_id,False)
        elif ev['prefix'] == '删除':
            await update_verify_state(bot,ev,user_id,True)
        elif ev['prefix'] == '退出审核':
            VerifyImageProcess[user_id] = VerifyImageProcess[user_id]._replace(state = False)
    except:
        logger.error(traceback.format_exc())
        await bot.send(ev, '出了点小问题，其实我觉得这图片挺涩的~')
        

@sv.on_prefix('快速审核')
async def quick_verify(bot, ev:CQEvent):
    id = str(ev.message).strip()
    user_id = int(ev["user_id"])
    if user_id not in verify_group:
        await bot.send(ev, '你谁啊你，不是管理员没资格审核色图哦~')
        return
    if not id:
        await bot.send(ev, "请在后面加上要通过的涩图序号f~")
        return
    try:
        verifyDao().update_verify_stats(id,0)
        await bot.send(ev, f'色图{id}审核通过')
    except:
        logger.error(traceback.format_exc())
        await bot.send(ev, "出了点小问题，但一定不是我的问题~")

@sv.on_fullmatch(('上传统计'))
async def verify_complete(bot, ev: CQEvent):
    try:
        sumnumber = normalDao().get_image_count()[0]
        text = f"当前图库总数{sumnumber}："
        results = normalDao().get_image_upload_rank()

        for i,raw in enumerate(results):
            user = raw[0]
            number = raw[1]
            text = text +f"\n第{str(i+1)}名："+ f'[CQ:at,qq={str(user)}] '+f'上传{str(number)}张'
        await bot.send(ev,text)
    except:
        logger.error(traceback.format_exc())

#@sv.on_prefix(('sql'))
#async def choose_setu(bot, ev):
#    uid = ev['user_id']
#    if not _nlmt.check(uid):
#        await bot.send(ev, EXCEED_NOTICE, at_sender=True)
#        return
#    if not _flmt.check(uid):
#        await bot.send(ev, '您冲得太快了，请稍候再冲', at_sender=True)
#        return
#    _flmt.start_cd(uid)
#    _nlmt.increase(uid) 
#    sql_result = str(ev.message).strip().split(' ',1)
#    if int(sql_result[0])>10:
#        sql_result[0] = '10'
#    sql = "SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify FROM LocalSetu where " + sql_result[1] +" ORDER BY random() limit "+ sql_result[0]
#    print(sql)
#    try:
#        test_conn()
#        cursor.execute(sql)
#        conn.commit()
#        result = cursor.fetchall()
#        if not result:
#           await bot.send(ev, '该群友xp不存在~~~')
#           return
#        for raw in result:
#            id = raw[0]
#            url=os.path.join(setu_folder,raw[1])
#            anti_url = os.path.join(setu_folder,raw[2])
#            user = raw[3]
#            date = raw[4]
#            tag = raw[5]
#            pixiv_tag = raw[6]
#            pixiv_id = raw[7]
#            verify = raw[9]
#            if raw[2]:
#                url = anti_url
#            if verify:
#                await bot.send(ev,"该图正在等待审核，暂不支持查看~")
#                return
#            if tag:
#                tag = f'当前TAG为空，您可以发送修改TAG{id}进行编辑~'
#            else:
#                tag = f'自定义TAG:{str(tag)}'
#            if pixiv_id :
#                pixiv_url = "https://pixiv.net/i/"+ str(pixiv_id)
#                await bot.send(ev, str(MessageSegment.image(f'file:///{os.path.abspath(url)}') + f'\n涩图ID:{id} 来源[CQ:at,qq={str(user)}]'+ f'\n{str(tag)}'+f'\nPixivTAG:{pixiv_tag}' +f'\n{pixiv_url}' +f'\n支持ID、来源、TAG模糊查询哦~'))
#            else:
#                await bot.send(ev, str(MessageSegment.image(f'file:///{os.path.abspath(url)}') + f'\n涩图ID:{id} 来源[CQ:at,qq={str(user)}]'+ f'\n{str(tag)}'+f'\nPixivTAG:{pixiv_tag}' +f'\n支持ID、来源、TAG模糊查询哦~'))
#    except CQHttpError:
#        sv.logger.error(f"发送图片{id}失败")
#        try:
#            await bot.send(ev, 'T T涩图不知道为什么发不出去勒...tu')
#        except:
#            pass
#         
#
@sv.on_prefix(('PID','pid'))
async def from_pid_get_image(bot, ev: CQEvent):
    id = str(ev.message).strip()
    if not id or not id.isdigit():
        await bot.send(ev, "请在后面加上要查看的涩图P站id~")
        return
    try:      
        pixiv_tag,pixiv_tag_t,r18,pixiv_url= await get_pixiv_tag_url(id,0)
        if not pixiv_tag:
            await bot.send(ev, '无法获取图片，该图片可能已被删除')
            return
        pixiv_proxy_url = re.sub(r"^https://(.*?)/",pximgUrl,pixiv_url)
        await bot.send(ev, '正在获取图片。。。请稍后。')
        msg = await anti_image_temporary(id,pixiv_proxy_url)
        await bot.send(ev, msg)
    except CQHttpError:
        logger.warning(traceback.format_exc())
        sv.logger.error(f"发送图片{id}失败")
        try:
            await bot.send(ev, 'T T涩图不知道为什么发不出去勒...tu')
        except:
            logger.warning(traceback.format_exc())
            pass

@sv.on_prefix('重新下载')
async def redownload_img_from_tencent(bot, ev):
    try:
        id = str(ev.message).strip()
        user = ev['user_id']
        if not id or not id.isdigit():
            await bot.send(ev, "请在后面加上要重新下载的色图")
            return
        msg = await redownload_from_tencent(id)
        await bot.send(ev,str(msg))
        return
    except:
        logger.error(traceback.format_exc())

@sv.on_prefix(('重新自动审核', '重新获取TAG'))
async def start_auto_verify(bot, ev: CQEvent):
    try:
        id = str(ev.message).strip()
        user = ev['user_id']
        if not id or not id.isdigit():
            await bot.send(ev, "请在后面加上起始ID")
            return
        if int(user) not in verify_group:
            await bot.send(ev,'你谁啊你，不是管理员没资格审核色图哦~')
            return
        else:
            txt = await auto_verify(id)
            await bot.send(ev,txt)
    except:
        logger.error(traceback.format_exc())
        
@sv.on_fullmatch(('更新数据库列表'))
async def start_update_db(bot, ev: CQEvent):
    try:
        user = ev['user_id']
        if int(user) != hoshino.config.SUPERUSERS[0]:
            await bot.send(ev,'你谁啊你，不是SUPERUSER没资格操作数据库哦~')
            return
        else:
            update_db()
            await bot.send(ev,'数据库更新完成')
    except:
        logger.error(traceback.format_exc())

logger.add(
    str(dir_path/"logs/error.log"),
    rotation="00:00",
    retention="1 week",
    diagnose=False,
    level="ERROR",
    encoding="utf-8",
)
logger.add(
    str(dir_path/"logs/info.log"),
    rotation="00:00",
    retention="1 week",
    diagnose=False,
    level="INFO",
    encoding="utf-8",
)
logger.add(
    str(dir_path/"logs/warning.log"),
    rotation="00:00",
    retention="1 week",
    diagnose=False,
    level="WARNING",
    encoding="utf-8",
)


@sv.scheduled_job('cron',hour='4')
async def re_download_verify():
    bot = hoshino.get_bot()
    superid = hoshino.config.SUPERUSERS[0]
    results = normalDao().get_tecent_url_list()
    for row in results:
        txt = await redownload_from_tencent(row[0])
    await bot.send_private_msg(user_id=superid, message='自动下载本地缺失文件完成，开始自动审核并爬取缺失TAG')
    msg = await auto_verify(1)                                          #重新自动审核
    await bot.send_private_msg(user_id=superid, message=msg)
    return