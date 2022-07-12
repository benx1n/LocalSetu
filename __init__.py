import os
from tokenize import group
import hjson
import re
from nonebot.typing import State_T
import requests
import time
from PIL import Image
import hashlib
import threading
import asyncio
import traceback
from pathlib import Path


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
from .src.normal_function import update_tag,anti_image


verifies=config['verify_group']
setu_folder = R.get('img/setu/').path
_max = 100
EXCEED_NOTICE = f'您今天已经冲过{_max}次了，请明早5点后再来！'
_nlmt = DailyNumberLimiter(_max)
_flmt = FreqLimiter(5)

#_REQUESTS_KWARGS = {
#'proxies':{
#      proxy
#      }
#}

SETU_help="""LocalSetu涩图帮助指南：
- -kkqyxp/kkntxp[keyword]：随机发送色图/男同图，其中keyword为可选参数，支持ID、@上传者、TAG模糊查询
- -上传色/男图[TAG][图片][TAG][图片][TAG][图片]，其中TAG为可选参数，可跟多张图片
- -上传色/男图[无参数]：进入上传模式，该模式下用户发送的所有图片均视为上传，无操作20秒后自动退出
- -查看原图[ID]：可用于保存原画画质的色图
- -删除色图[ID]：删除指定ID色图，非审核组成员仅可删除本人上传的色图，他人色图将会推送至审核组
- -修改TAG[ID][TAG]：修改指定ID的自定义TAG
- -反和谐[ID]：色图被TX屏蔽时使用该指令，进行一次反和谐，后续发送色图均使用反和谐后文件
- -PID/pid[ID]:通过pixivID查看P站原图
- -上传统计：让我康康谁才是LSP！
- -[BETA]sql：批量涩图，sql+数量+空格+条件，如sql10 id>1000，条件可参考sql表结构
- -仓库地址：https://github.com/pcrbot/LocalSetu 有问题欢迎提issue
=======Shokaku限定功能：
- -gkd：在线图库，使用方法[r18]TAG+涩图，可使用 & 和 | 将多个TAG进行组合，如r18明日方舟|碧蓝航线&白丝|黑丝gkd，则会查找（明日方舟或碧蓝航线）且是（黑丝或白丝）的r18涩图
- -搜图：@bot+图或发送搜图进入搜图模式，可带参数指定搜索引擎 --book为搜本子，--anime为搜番剧
=======审核组用户有以下指令：
= =审核色图[上传][删除]：进入审核模式，每次发送待审核的色图，使用指令[保留][删除]后自动发送下一张，发送[退出审核]或20秒无操作自动退出
= =快速审核[ID]：快速通过指定ID的申请（默认保留）
= =重新自动审核/重新获取TAG[起始ID]：重新审核/获取TAG，适用于首次上传由于SauceNAO接口限制而导致的批量自动审核失败
"""

#class MyThread(threading.Thread):
#    def __init__(self,func,args,name=''):
#        threading.Thread.__init__(self)
#        self.func = func
#        self.name = name
#        self.args = args
#
#    def run(self):
#       #print('开始执行',self.name,' 在：',ctime())
#        self.res = self.func(*self.args)
#        #print(self.name,'结束于：',ctime())
#
#    def getResult(self):
#        return self.res

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
        traceback.print_exc()
        sv.logger.error(f"发送图片{id}失败")
        try:
            await bot.send(ev, 'T T涩图不知道为什么发不出去勒...正在尝试反和谐后发送')
            msg = await anti_image(id)
            await bot.send(ev, msg)
        except:
            pass

@sv.on_prefix(('查看原图','看看原图','看看大图','查看大图'))
async def get_original_setu(bot, ev: CQEvent):
    id = str(ev.message).strip()
    if not id or not id.isdigit():
        await bot.send(ev, "请在后面加上要查看的涩图序号~")
        return
    try:
        msg,url = await get_original_image(id,bot,ev)
        if url:
            await bot.send(ev, f"{str(MessageSegment.image(f'file:///{os.path.abspath(url)}'))}\n{msg}")
        else:
            await bot.send(ev, msg)
    except CQHttpError:
        traceback.print_exc()
        sv.logger.error(f"发送图片{id}失败")
        try:
            await bot.send(ev, 'T T涩图不知道为什么发不出去勒...可能是被TXban了')
        except:
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
    except Exception as e:
        traceback.print_exc()
        await quit_load(user_id)
        await bot.send(ev, 'wuwuwu~上传失败了~')
        
#监听:消息类型的图片
@sv.on_message()
async def is_load_image(bot, ev:CQEvent):
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
    
#监听:文件类型的图片  
@sv.on_notice()
async def is_load_file(session: NoticeSession):
    ev = session.event
    user_id=ev['user_id']
    if not LoadImageProcess[user_id].state:       #是否处于上传模式
        return
    if not ((str(ev).find("'file': {")+1)):  #判断收到的信息是否为文件，不是就退出
        return
    bot = get_bot()
    await reset_load_time(user_id)
    await load_image(bot,ev,LoadImageProcess[user_id].is_man)
  
@sv.on_prefix(('删除涩图', '删除色图','删除男图'))
async def del_image(bot, ev: CQEvent):
    id = str(ev.message).strip()
    user = ev['user_id']
    if not id or not id.isdigit():
        await bot.send(ev, "请在后面加上要删除的涩图序号~")
        return
    msg = await delete_image(id,user,bot,ev)
    await bot.send(ev,msg)

@sv.on_prefix(('修改TAG','修改tag'))
async def modify_tag(bot, ev: CQEvent):
    if not str(ev.message).strip():
        await bot.send(ev, '请在指令后添加ID和TAG哦~以空格区分')
        return
    try:
        id,tag=str(ev.message).split(' ', 1 )
        await update_tag(tag,id)
        await bot.send(ev, f'涩图{id}的TAG已更新为{tag}')
    except Exception as e:
        await bot.send(ev, '请在指令后添加ID和TAG哦~以空格区分')

@sv.on_prefix(('反和谐'))
async def Anti_harmony(bot, ev: CQEvent):
    id = str(ev.message).strip()
    if not id or not id.isdigit():
        await bot.send(ev, '请输入要反和谐的图片ID')
    else:
        msg = await anti_image(id)
        await bot.send(ev, msg)
    
#
#
#class Verify:
#    def __init__(self):
#        self.url=""     #审核的色图url
#        self.switch=0   #当前是否处于审核状态 0 不处于 1处于
#        self.id=-1     #审核的色图id
#        self.sql_state=0 #是否执行过sql
#        self.flag=0 #执行次数
#ve=Verify()
#
#@sv.on_fullmatch(('审核色图上传','审核色图删除'))
#async def verify_setu(bot, ev: CQEvent):
#    if int(ev["user_id"]) not in verifies:
#        await bot.send(ev, '你谁啊你，不是管理员没资格审核色图哦~')
#        return
#    if ev['prefix'] == '审核色图上传':
#        sql="select url,user,date,id,man from LocalSetu where verify=1 ORDER BY id DESC limit 1"
#    elif ev['prefix'] == '审核色图删除':
#        sql="select url,user,date,id,man from LocalSetu where verify=2 ORDER BY id DESC limit 1"
#    ve.sql_state,ve.flag=0,0
#    try:
#        while ve.flag < 40:
#            ve.flag = ve.flag + 1
#            if not ve.sql_state:
#                test_conn()
#                cursor.execute(sql)
#                conn.commit()
#                results = cursor.fetchone()
#                if not results:
#                    await bot.send(ev, '当前没有要审核图片哦，摸鱼大胜利~')
#                    return                                 
#                ve.url=os.path.join(setu_folder,results[0])
#                user=results[1]
#                date=results[2]
#                ve.id=results[3]
#                man=results[4]
#                man_text = '色图'
#                if man:
#                    man_text = '男图'
#                await bot.send(ev, '当前审核的图片为'+str(MessageSegment.image(f'file:///{os.path.abspath(ve.url)}'))+f'ID：{ve.id}\n来源为[CQ:at,qq={str(user)}]\n类型为:{man_text}\n上传时间:{date}')
#                ve.sql_state,ve.switch = 1,1
#            await asyncio.sleep(0.5)
#        await bot.send(ev, '20秒过去了，审核结束~')
#        return
#    except Exception as e:
#        await bot.send(ev, 'QAQ~审核的时候出现了问题，但一定不是我的问题~')
#
#@sv.on_fullmatch(('保留','删除','退出审核'))
#async def verify_complete(bot, ev: CQEvent):
#    if not ve.switch or int(ev["user_id"]) not in verifies:
#        return
#    try:
#        test_conn()
#        if ev['prefix'] == '保留':
#            sql="update LocalSetu set verify=0 where id = ?"
#            cursor.execute(sql,(ve.id,))
#            conn.commit()
#            await bot.send(ev, '当前图片审核通过'+str(MessageSegment.image(f'file:///{os.path.abspath(ve.url)}'))+f'id为{ve.id}')
#        elif ev['prefix'] == '删除':
#            os.remove(ve.url)
#            sql="delete from LocalSetu where id = ?"
#            cursor.execute(sql,(ve.id,))
#            conn.commit()
#            await bot.send(ev, 'OvO~不合格的涩图删掉了~')
#        elif ev['prefix'] == '退出审核':
#            ve.flag = 40
#            return 
#        ve.switch,ve.flag,ve.sql_state= 0,0,0
#    except:
#        await bot.send(ev, '出了点小问题，其实我觉得这图片挺涩的~')
#    return
#
#@sv.on_prefix('快速审核')
#async def quick_verify(bot, ev:CQEvent):
#    id = str(ev.message).strip()
#    user = ev['user_id']
#    if int(user) not in verifies:
#        await bot.send(ev,'你谁啊你，不是管理员没资格审核色图哦~')
#        return
#    if not id:
#        await bot.send(ev, "请在后面加上要通过的涩图序号f~")
#        return
#    try:
#        test_conn()
#        sql="update LocalSetu set verify=0 where id = ?"
#        cursor.execute(sql,(id,))
#        conn.commit()
#        await bot.send(ev, f'色图{id}审核通过')
#    except Exception as e:
#        await bot.send(ev, "出了点小问题，但一定不是我的问题~")
#
#@sv.on_fullmatch(('上传统计'))
#async def verify_complete(bot, ev: CQEvent):
#    sql1 = "select count(*) as sumnumber from LocalSetu"
#    sql2 = "select user,count(user) as number from LocalSetu GROUP BY user ORDER BY number desc limit 10"
#    test_conn()
#    cursor.execute(sql1)
#    conn.commit()
#    results = cursor.fetchone()
#    sumnumber = results[0]
#    text = f"当前图库总数{sumnumber}："
#    cursor.execute(sql2)
#    conn.commit()
#    results = cursor.fetchall()
#    
#    for i,raw in enumerate(results):
#        user = raw[0]
#        number = raw[1]
#        text = text +f"\n第{str(i+1)}名："+ f'[CQ:at,qq={str(user)}] '+f'上传{str(number)}张'
#    await bot.send(ev,text)
#
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
#@sv.on_prefix(('PID','pid'))
#async def from_pid_get_image(bot, ev: CQEvent):
#    id = str(ev.message).strip()
#    if not id or id=="" or not id.isdigit():
#        await bot.send(ev, "请在后面加上要查看的涩图P站id~")
#        return
#    try:      
#        pixiv_tag,pixiv_tag_t,r18,pixiv_img_url=get_pixiv_tag_url(id,0)
#        if not pixiv_tag:
#            await bot.send(ev, '无法获取图片，该图片可能已被删除')
#            return
#        pixiv_img_url = pixiv_img_url.replace("i.pximg.net","i.pixiv.re")
#        
#        #####反和谐
#       # await bot.send(ev,f"{pixiv_img_url}") 
#        Anti_harmony_url=setu_folder+"/Anti_harmony_777"
#        await bot.send(ev, '正在获取图片。。。请稍后。')
#        new_download(pixiv_img_url, Anti_harmony_url)   
#        img=Image.open(Anti_harmony_url)
#        img=image_random_one_pixel(img)
#        Anti_harmony_url = Anti_harmony_url + '8'
#        img.save(Anti_harmony_url,'PNG',quality=75)
#
#     #   await bot.send(ev,f"{pixiv_img_url}")
#        
#        await bot.send(ev,str(MessageSegment.image(f'file:///{os.path.abspath(Anti_harmony_url)}'))+f'\n本图片进过反和谐，若有原图需要请从反代链接下载'+ f'\n原图链接：https://pixiv.net/i/{id}' + f'\n反代链接:{pixiv_img_url}')
#    except CQHttpError:
#        sv.logger.error(f"发送图片{id}失败")
#        try:
#            await bot.send(ev, 'T T涩图不知道为什么发不出去勒...tu')
#        except:
#            pass
#
#@sv.on_prefix('重新下载')
#async def redownload_img_from_tencent(bot, ev):
#    id = str(ev.message).strip()
#    user = ev['user_id']
#    if not id or id=="" or not id.isdigit():
#        await bot.send(ev, "请在后面加上要重新下载的色图")
#        return
#    txt = await redownload_from_tencent(id)
#    await bot.send(ev,str(txt))
#    return
#
#@sv.on_prefix(('重新自动审核', '重新获取TAG'))
#async def auto_verify(bot, ev: CQEvent):
#    id = str(ev.message).strip()
#    user = ev['user_id']
#    if not id or id=="" or not id.isdigit():
#        await bot.send(ev, "请在后面加上起始ID")
#        return
#    if int(user) not in verifies:
#        await bot.send(ev,'你谁啊你，不是管理员没资格审核色图哦~')
#        return
#    else:
#        txt = await auto_verify(id)
#        await bot.send(ev,txt)
#
#async def redownload_from_tencent(id):
#    test_conn
#    sql="SELECT url,tencent_url FROM LocalSetu where id = ?"
#    cursor.execute(sql,(id,))
#    result = cursor.fetchone()
#    if not result:
#        txt = f'id{id}不存在~~~'
#        return txt
#    if not result[1]:
#        txt = f'id{id}的腾讯服务器url不存在~~~'
#        return txt
#    local_url = os.path.join(setu_folder,result[0])
#    if not os.path.exists(os.path.abspath(local_url)):
#        try:
#            await download(result[1], local_url)
#            txt = f'id{id}下载成功'
#        except:
#            txt = f'id{id}下载失败，可能是腾讯服务器url过期了~'
#    else:
#        txt = f'id{id}本地文件已存在哦~'
#    return txt
#
#async def auto_verify(id):
#    test_conn
#    sql="SELECT id,url FROM LocalSetu where (pixiv_id = 0 or verify = 1) and id >= ?"
#    #sql="SELECT id,url FROM bot.localsetu where id = 759 or id =760 or id=761 ORDER BY id limit 1"
#    cursor.execute(sql,(id,))
#    results = cursor.fetchall()
#    id = 0
#    success = 0
#    failed = 0
#    for row in results:
#        id = row[0] #参数初始化
#        url= setu_folder+'/'+row[1]
#        #url= 'https://pixiv.cat/92252996.jpg'
#        pixiv_tag=''
#        pixiv_tag_t=''
#        pixiv_img_url=''
#        r18=0
#        print(f'id='+ str(id))
#        pixiv_id,index_name=get_pixiv_id(url)
#        if not pixiv_id:
#            #print('获取失败了~')
#            #await bot.send(ev, f'id:{id}自动审核失败，可能刚上传至P站，请进行人工审核哦~[CQ:at,qq={str(user)}]')
#            sv.logger.info(f'id:{id}未通过自动审核,可能刚上传至P站或无法访问saucenao')
#            failed += 1
#            #time.sleep(1)
#        else:
#            page = re.search(r'_p(\d+)',index_name,re.X)
#            if not page:
#                pagenum = 0
#            else:
#                pagenum = page.group(1)
#            pixiv_tag,pixiv_tag_t,r18,pixiv_img_url=get_pixiv_tag_url(pixiv_id,pagenum)
#            if not pixiv_tag:
#                #print('无法获取原画，该原画可能已被删除')
#                #await bot.send(ev, f'id:{id}自动审核失败，可能原画已被删除，请进行人工审核哦~[CQ:at,qq={str(user)}]')
#                sv.logger.info(f'id:{id}未通过自动审核,可能原画已被删除或无法访问P站API')
#                failed += 1
#                #time.sleep(1)
#            else:
#                pixiv_img_url = pixiv_img_url.replace("i.pximg.net","i.pixiv.re")
#                sql = "update LocalSetu set pixiv_id = ?,pixiv_tag = ?,pixiv_tag_t = ?,r18 = ?,pixiv_url = ?,verify = ? where id = ?"
#                cursor.execute(sql,(pixiv_id,pixiv_tag,pixiv_tag_t,r18,pixiv_img_url,0,id))
#                conn.commit()
#                #print(pixiv_id,pixiv_tag,pixiv_tag_t,r18,pixiv_img_url)
#                #await bot.send(ev, f'id:{id}上传成功，自动审核通过\n已自动为您获取原图PixivID:{pixiv_id}\n'+f"发送'查看原图+ID'即可")
#                sv.logger.info(f'id:{id}通过自动审核,已自动为您获取原图PixivID:{pixiv_id}')
#                success += 1
#        await asyncio.sleep(5)
#    return f'重新自动审核完成\n成功'+str(success)+f'张\n失败'+str(failed)+f'张'
#
#@sv.scheduled_job('cron',hour='4')
#async def re_download_verify():
#    bot = hoshino.get_bot()
#    superid = hoshino.config.SUPERUSERS[0]
#    test_conn
#    sql="SELECT id FROM LocalSetu where tencent_url is not NULL"        #下载缺失文件
#    cursor.execute(sql)
#    results = cursor.fetchall()
#    for row in results:
#        txt = await redownload_from_tencent(row[0])
#    msg = '自动下载本地缺失文件完成'
#    await bot.send_private_msg(user_id=superid, message=msg)
#    msg = await auto_verify(1)                                          #重新自动审核
#    await bot.send_private_msg(user_id=superid, message=msg)
#    return