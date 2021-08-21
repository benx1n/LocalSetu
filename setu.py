import os
import random
import re
import traceback
from nonebot.typing import State_T
import requests
import time
import pymysql
import aiohttp
from nonebot.exceptions import CQHttpError

from hoshino import R, Service, priv
from hoshino.util import FreqLimiter, DailyNumberLimiter
from hoshino.typing import CQEvent, MessageSegment
from nonebot import on_command


_max = 100
EXCEED_NOTICE = f'您今天已经冲过{_max}次了，请明早5点后再来！'
_nlmt = DailyNumberLimiter(_max)
_flmt = FreqLimiter(5)

sv = Service('setu', manage_priv=priv.SUPERUSER, enable_on_default=True, visible=False)
setu_folder = R.get('img/setu/').path
conn = pymysql.connect(host="localhost",user="root",password="Jwh13372319912.",database="bot" )
cursor = conn.cursor()

def test_conn():
    try:
        conn.ping()
    except:
        conn = pymysql.connect(
            host="localhost",
            user="root",
            password="Jwh13372319912.",
            database="bot")
        cursor = conn.cursor()

def setu_gener():
    while True:
        filelist = os.listdir(setu_folder)
        random.shuffle(filelist)
        for filename in filelist:
            if os.path.isfile(os.path.join(setu_folder, filename)):
                yield R.get('img/setu/', filename)

setu_gener = setu_gener()

def get_setu():
    return setu_gener.__next__()

async def download(url, path):
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            content = await resp.read()
            with open(path, 'wb') as f:
                f.write(content)
                
@sv.on_fullmatch(('来份涩图', '来份色图', '来点色图', '来点涩图', '色图', '涩图'))
async def setu(bot, ev):
    """随机叫一份涩图，对每个用户有冷却时间"""
    uid = ev['user_id']
    if not _nlmt.check(uid):
        await bot.send(ev, EXCEED_NOTICE, at_sender=True)
        return
    if not _flmt.check(uid):
        await bot.send(ev, '您冲得太快了，请稍候再冲', at_sender=True)
        return
    _flmt.start_cd(uid)
    _nlmt.increase(uid)

    # conditions all ok, send a setu.
    pic = get_setu()
    try:
        await bot.send(ev, os.path.split(str(pic.path))[1]+pic.cqcode)
    except CQHttpError:
        sv.logger.error(f"发送图片{pic.path}失败")
        try:
            await bot.send(ev, '涩图太涩，发不出去勒...')
        except:
            pass

@on_command('偷偷给你色图', aliases=('偷偷给你色图'), only_to_me=True)
async def test(session):
    message=session.event['message']
    #for mes in message:
    #    print("----",mes)
   # print("==========================================",message)
  #  await session.send("爬")
    try:
        test_conn()
        if not str(message).strip() or str(message).strip()=="":
            await session.send('发涩图发涩图~')
            return
        tag = ""
        for i,seg in enumerate(message):
            if seg.type == 'text':
                tag = str(seg).lstrip('偷偷给你色图 ')
            elif seg.type == 'image':
                img_url = seg.data['url']
                setu_name = seg.data['file']
                await download(img_url, os.path.join(setu_folder,setu_name))
                sql="REPLACE INTO localsetu VALUES (\'%s\',%s,NOW(),\'%s\')"%(setu_name,str(session.event['user_id']),tag)
                #await bot.send(ev,str(sql))
                cursor.execute(sql)
                conn.commit()
                await session.send(f'涩图收到了~如需删除请联系管理员发送删除色图{setu_name}')
    except Exception as e:
        traceback.print_exc()
        print("yichang",e)
        await session.send('wuwuwu~涩图不知道在哪~')

@sv.on_prefix(('kkqyxp','看看群友xp','看看群友性癖'))
async def choose_setu(bot, ev):
    uid = ev['user_id']
    if not _nlmt.check(uid):
        await bot.send(ev, EXCEED_NOTICE, at_sender=True)
        return
    if not _flmt.check(uid):
        await bot.send(ev, '您冲得太快了，请稍候再冲', at_sender=True)
        return
    _flmt.start_cd(uid)
    _nlmt.increase(uid)
   # text = 
    id1=0
    if not str(ev.message).strip() or str(ev.message).strip()=="":
        id1=1
    elif ev.message[0].type == 'at':
        id1 = 2
        user = int(ev.message[0].data['qq'])
    #else:
     #   await bot.finish(ev, '参数格式错误, 请重试')
    # conditions all ok, send a setu.
    try:
        test_conn()
        if id1==0:#带tag
            sql="SELECT * FROM bot.localsetu where tag like \'%%%s%%\' OR url like \'%%%s%%\' ORDER BY RAND() limit 1"%(str(ev.message).strip(),str(ev.message).strip())
        if id1==1:#全随机
            sql="SELECT * FROM bot.localsetu ORDER BY RAND() limit 1"
        elif id1==2:#指定人
            sql="SELECT * from localsetu where user = \'"+str(user)+"\'ORDER BY RAND() limit 1"
        cursor.execute(sql)
        results = cursor.fetchall()
        if not results:
           await bot.send(ev, '该群友xp不存在~~~')
        for row in results:
            setuname=os.path.join(setu_folder,row[0])
            user = row[1]
            date = row[2]
            tag = row[3]
        await bot.send(ev, str(MessageSegment.image(f'file:///{os.path.abspath(setuname)}') + f'\n客官，这是您点的涩图~涩图来源[CQ:at,qq={str(user)}]'+ f'TAG:{str(tag)}' + f'\n上传日期{str(date)}'))
    except CQHttpError:
        sv.logger.error(f"发送图片{setuname}失败")
        try:
            await bot.send(ev, 'T T涩图不知道为什么发不出去勒...tu')
        except:
            pass

@sv.on_prefix(('kkntxp','看看男同xp','看看男同性癖'))
async def choose_setu(bot, ev):
    uid = ev['user_id']
    if not _nlmt.check(uid):
        await bot.send(ev, EXCEED_NOTICE, at_sender=True)
        return
    if not _flmt.check(uid):
        await bot.send(ev, '您冲得太快了，请稍候再冲', at_sender=True)
        return
    _flmt.start_cd(uid)
    _nlmt.increase(uid)
   # text = 
    id1=0
    if not str(ev.message).strip() or str(ev.message).strip()=="":
        id1=1
    elif ev.message[0].type == 'at':
        id1 = 2
        user = int(ev.message[0].data['qq'])
    #else:
     #   await bot.finish(ev, '参数格式错误, 请重试')
    # conditions all ok, send a setu.
    try:
        test_conn()
        if id1==0:
            sql="SELECT * FROM bot.localsetu where tag like \'%%%s%%\' OR url like \'%%%s%%\' ORDER BY RAND() limit 1"%(str(ev.message).strip(),str(ev.message).strip())
        if id1==1:
            sql="SELECT * FROM bot.localsetu ORDER BY RAND() limit 1"
        elif id1==2:
            sql="SELECT * from localsetu where user = \'"+str(user)+"\'ORDER BY RAND() limit 1"
        cursor.execute(sql)
        results = cursor.fetchall()
        if not results:
           await bot.send(ev, '该群友xp不存在~~~')
        for row in results:
            setuname=os.path.join(setu_folder,row[0])
            user = row[1]
        await bot.send(ev, str(MessageSegment.image(f'file:///{os.path.abspath(setuname)}') + f'\n客官，这是您点的涩图~涩图来源[CQ:at,qq={str(user)}]'))
    except CQHttpError:
        sv.logger.error(f"发送图片{setuname}失败")
        try:
            await bot.send(ev, 'T T涩图不知道为什么发不出去勒...tu')
        except:
            pass

@sv.on_prefix('上传色图')
async def give_setu(bot, ev:CQEvent):
    try:
        test_conn()
        if not str(ev.message).strip() or str(ev.message).strip()=="":
            await bot.send(ev, '发涩图发涩图~')
            return
        tag = ""
        for i,seg in enumerate(ev.message):
            if seg.type == 'text':
                tag=str(seg).strip()
            elif seg.type == 'image':
                img_url = seg.data['url']
                setu_name = seg.data['file']
                await download(img_url, os.path.join(setu_folder,setu_name))
                sql="REPLACE INTO localsetu VALUES (\'%s\',%s,NOW(),\'%s\')"%(setu_name,str(ev['user_id']),tag)
                #await bot.send(ev,str(sql))
                cursor.execute(sql)
                conn.commit()
                await bot.send(ev, f'涩图收到了~如需删除请联系管理员发送删除色图{setu_name}')
    except Exception as e:
        print("yichang",e)
        await bot.send(ev, 'wuwuwu~涩图不知道在哪~')

@sv.on_keyword('上传男图')
async def give_setu(bot, ev:CQEvent):
    try:
        test_conn()
        ticks = int(time.time())
        if not str(ev.message).strip() or str(ev.message).strip()=="":
            await bot.send(ev, '发涩图发涩图~')
            return
        for i,seg in enumerate(ev.message):
            if seg.type == 'text':
                tag=str(seg).strip()
            elif seg.type == 'image':
                img_url = seg.data['url']
                setu_name = seg.data['file']
                await download(img_url, os.path.join(setu_folder,setu_name))
                sql="REPLACE INTO localsetu_man VALUES (\'%s\',%s,NOW(),\'%s\')"%(setu_name,str(ev['user_id']),tag)
                cursor.execute(sql)
                conn.commit()
                await bot.send(ev, f'涩图收到了~如需删除请联系管理员发送删除色图{setu_name}')
    except Exception as e:
        print("yichang",e)
        await bot.send(ev, 'wuwuwu~涩图不知道在哪~')

@sv.on_prefix(('删除涩图', '删除色图','删除男图'))
async def del_setu(bot, ev: CQEvent):
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev, '抱歉，您非管理员，无此指令使用权限')
    setu_name = str(ev.message).strip()
    #await bot.send(ev,setu_name)
    if not setu_name or setu_name=="":
        await bot.send(ev, '请在后面加上要删除的涩图名~')
        return
    try:
        test_conn()
        #await bot.send(ev,str(os.path.join(setu_folder, setu_name)))
        os.remove(os.path.join(setu_folder, setu_name))
        sql="delete from localsetu,localsetu_man where url = %s"
        cursor.execute(sql,(setu_name,))
        conn.commit()
        await bot.send(ev, 'OvO~涩图删掉了~')
    except:
        await bot.send(ev, 'QAQ~删涩图的时候出现了问题，但一定不是我的问题~')