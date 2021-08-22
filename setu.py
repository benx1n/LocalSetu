import os
import json
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


with open('./hoshino/modules/setu/config.json') as json_data_file:
    config = json.load(json_data_file)

host = config['mysql']['host']
user=config['mysql']['user']
password=config['mysql']['password']
database=config['mysql']['database']

_max = 100
EXCEED_NOTICE = f'您今天已经冲过{_max}次了，请明早5点后再来！'
_nlmt = DailyNumberLimiter(_max)
_flmt = FreqLimiter(5)

sv = Service('setu', manage_priv=priv.SUPERUSER, enable_on_default=True, visible=False)
setu_folder = R.get('img/setu/').path
conn = pymysql.connect(host=host,user=user,password=password,database=database)
cursor = conn.cursor()
def test_conn():
    try:
        conn.ping()
    except:
        conn = pymysql.connect(host=host,user=user,password=password,database=database)
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
                
'''旧私聊方法，已弃用
@on_command(('偷偷给你色图','偷偷给你男图'), aliases=('偷偷给你色图','偷偷给你男图'), only_to_me=True)
async def test(session):
    message=session.event['message']
    print(session.event)
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
        is_man = 0
        matchObj = re.match(r'偷偷给你(.+?)图(.+?)\[CQ',str(message),re.X)
        if matchObj.group(1) == '男':
            is_man = 1
        for i,seg in enumerate(message):
            if seg.type == 'text':
                if i == 0 :
                    tag = matchObj.group(2).strip()
                else:
                    tag = str(seg).lstrip()
            elif seg.type == 'image':
                img_url = seg.data['url']
                setu_name = seg.data['file']
                await download(img_url, os.path.join(setu_folder,setu_name))
                sql="REPLACE INTO localsetu VALUES (\'%s\',%s,NOW(),\'%s\',%s)"%(setu_name,str(session.event['user_id']),tag,is_man)
                #await bot.send(ev,str(sql))
                cursor.execute(sql)
                conn.commit()
                await session.send(f'涩图收到了~TAG为{tag},如需删除请联系管理员发送删除色图{setu_name}')
    except Exception as e:
        traceback.print_exc()
        print("yichang",e)
        await session.send('wuwuwu~涩图不知道在哪~')
'''
@sv.on_prefix(('kkqyxp','看看群友xp','看看群友性癖','kkntxp','看看男同xp','看看男同性癖'))
async def choose_setu(bot, ev):
    print(ev)
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
    searchtag = str(ev.message).strip()
    if not searchtag or searchtag=="":
        id1=1
    elif ev.message[0].type == 'at':
        id1 = 2
        user = int(ev.message[0].data['qq'])
    #else:
     #   await bot.finish(ev, '参数格式错误, 请重试')
    # conditions all ok, send a setu.
    try:
        test_conn()
        is_man = 0
        if ev['prefix'] == ('kkntxp'or '看看男同xp' or '看看男同性癖'):
            is_man = 1
        if id1==0:#带tag
            if searchtag.isdigit(): #id
                sql="SELECT * FROM bot.localsetu where man = %s AND id = \'%s\' ORDER BY RAND() limit 1"%(is_man,searchtag)
            else:   #tag
                sql="SELECT * FROM bot.localsetu where man = %s AND (tag like \'%%%s%%\' OR pixiv_tag like \'%%%s%%\') ORDER BY RAND() limit 1"%(is_man,searchtag,searchtag)
        if id1==1:#全随机
            sql="SELECT * FROM bot.localsetu where man = %s ORDER BY RAND() limit 1"%is_man
        elif id1==2:#指定人
            sql="SELECT * from localsetu where man = %s AND user = \'%s\' ORDER BY RAND() limit 1"%(is_man,str(user))
        cursor.execute(sql)
        results = cursor.fetchall()
        if not results:
           await bot.send(ev, '该群友xp不存在~~~')
        for row in results:
            id = row[0]
            url=os.path.join(setu_folder,row[1])
            user = row[2]
            date = row[3]
            tag = row[4]
            pixiv_tag = row[7]
        if tag =='':
            tag = f'当前TAG为空，您可以发送修改TAG{row[0]}进行编辑~'
        else:
            tag = f'自定义TAG:{str(tag)}'
        await bot.send(ev, str(MessageSegment.image(f'file:///{os.path.abspath(url)}') + f'\n涩图ID:{id} 来源[CQ:at,qq={str(user)}]'+ f'\n{str(tag)}'+f'\nPixivTAG:{pixiv_tag}' + f'\n上传日期{str(date)}'+f'\n支持ID、来源、TAG模糊查询哦~'))
    except CQHttpError:
        sv.logger.error(f"发送图片{row[0]}失败")
        try:
            await bot.send(ev, 'T T涩图不知道为什么发不出去勒...tu')
        except:
            pass


@sv.on_prefix(('上传色图','上传男图'))
async def give_setu(bot, ev:CQEvent):
    try:
        print(ev)
        test_conn()
        if not str(ev.message).strip() or str(ev.message).strip()=="":
            await bot.send(ev, '发涩图发涩图~')
            return
        tag = ""
        is_man = 0
        if ev['prefix'] == '上传男图':
            is_man = 1
        for i,seg in enumerate(ev.message):
            if seg.type == 'text':
                tag=str(seg).strip()
            elif seg.type == 'image':
                img_url = seg.data['url']
                setu_name = seg.data['file']
                sql="SELECT id FROM localsetu where url = '%s'"%str(seg.data['file'])
                cursor.execute(sql)
                result = cursor.fetchone()
                if not result:
                    await download(img_url, os.path.join(setu_folder,setu_name))
                    sql="INSERT IGNORE INTO localsetu (id,url,user,date,tag,man) VALUES (NULL,\'%s\',%s,NOW(),\'%s\',%s)"%(setu_name,str(ev['user_id']),tag,is_man)
                    cursor.execute(sql)
                    #id=conn.insert_id()
                    id=cursor.lastrowid
                    conn.commit()
                    await bot.send(ev, f'涩图收到了~id为{id}\n自定义TAG为{tag}\n稍后会自动从P站获取TAG')
                else:
                    await bot.send(ev, f'涩图已经存在了哦~id为{result[0]}')
    except Exception as e:
        print("yichang",e)
        await bot.send(ev, 'wuwuwu~上传失败了~')


@sv.on_prefix(('删除涩图', '删除色图','删除男图'))
async def del_setu(bot, ev: CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        await bot.finish(ev, '抱歉，您非管理员，无此指令使用权限')
    id = str(ev.message).strip()
    if not id or id=="":
        await bot.send(ev, '请在后面加上要删除的涩图序号~')
        return
    try:
        test_conn()
        sql="select url from localsetu where id = %s"%id
        cursor.execute(sql)
        results = cursor.fetchall()
        if not results:
           await bot.send(ev, '请检查id是否正确~')
        for row in results:
            url=row[0]
        os.remove(os.path.join(setu_folder, row[0]))
        sql="delete from localsetu where id = %s"%id
        cursor.execute(sql)
        conn.commit()
        await bot.send(ev, 'OvO~涩图删掉了~')
    except Exception as e:
        print("yichang",e)
        await bot.send(ev, 'QAQ~删涩图的时候出现了问题，但一定不是我的问题~')

@sv.on_prefix(('修改TAG','修改tag'))
async def modify_tag(bot, ev: CQEvent):
    test_conn()
    if not str(ev.message).strip() or str(ev.message).strip()=="":
        await bot.send(ev, '请在指令后添加ID和TAG哦~以空格区分')
        return
    try:
        id,tag=str(ev.message).split(' ', 1 )
        sql="update localsetu set tag = \'%s\' where id = \'%s\'"%(tag,id)
        cursor.execute(sql)
        conn.commit()
        await bot.send(ev, f'涩图{id}的TAG已更新为{tag}')
    except Exception as e:
        print("yichang",e)
        await bot.send(ev, '请在指令后添加ID和TAG哦~以空格区分')