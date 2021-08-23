import os
import json
import random
import re
import traceback
from nonebot.typing import State_T
from numpy.lib.function_base import quantile
import requests
import time
from PIL import Image
import pymysql
import aiohttp
import numpy as np
import hashlib

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
conn = pymysql.connect(host=host,user=user,password=password,database=database,charset='utf8',autocommit = 1)
cursor = conn.cursor()
def test_conn():
    try:
        conn.ping()
    except:
        conn = pymysql.connect(host=host,user=user,password=password,database=database,charset='utf8',autocommit = 1)
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

#下面的函数随机更改图片的某个像素值，用于反和谐
def image_random_one_pixel(img1):  
    w,h=img1.size
    pots=[(0,0),(0,h-1),(w-1,0),(w-1,h-1)]
    pot=pots[random.randint(0,3)]
    print(pot)
   # pot_pixel=img1.getpixel(pot)
  #  rate=random.uniform(0,1)
 #   new_r=int(pot_pixel[h,w][0][0]*rate)
  #  new_g=int(pot_pixel[h,w][0][1]*rate)
  #  new_b=int(pot_pixel[h,w][0][2]*rate)
    img1.putpixel(pot,(random.randint(0,255),random.randint(0,255),random.randint(0,255)))
    return img1

#图片文件转为MD5
def image2MD5(filename):
    file = open(filename, "rb")
    md = hashlib.md5()
    md.update(file.read())
    res1 = md.hexdigest()
    print(res1)
    return res1+".image"

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
                sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,verify FROM bot.localsetu where man = %s AND id = \'%s\' ORDER BY RAND() limit 1"%(is_man,searchtag)
            else:   #tag
                sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,verify FROM bot.localsetu where man = %s AND (tag like \'%%%s%%\' OR pixiv_tag like \'%%%s%%\' OR pixiv_tag_t like \'%%%s%%\') ORDER BY RAND() limit 1"%(is_man,searchtag,searchtag)
        if id1==1:#全随机
            sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,verify FROM bot.localsetu where man = %s ORDER BY RAND() limit 1"%is_man
        elif id1==2:#指定人
            sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_tm,verify from localsetu where man = %s AND user = \'%s\' ORDER BY RAND() limit 1"%(is_man,str(user))
        cursor.execute(sql)
        #conn.commit()
        result = cursor.fetchone()
        if not result:
           await bot.send(ev, '该群友xp不存在~~~')
           return
        id = result[0]
        url=os.path.join(setu_folder,result[1])
        anti_url = os.path.join(setu_folder,result[2])
        user = result[3]
        date = result[4]
        tag = result[5]
        pixiv_tag = result[6]
        verify = result[7]
        if result[2] != '':
            url = anti_url
        if verify != 0:
            await bot.send(ev,"该图正在等待审核，暂不支持查看~")
            return
        if tag =='':
            tag = f'当前TAG为空，您可以发送修改TAG{id}进行编辑~'
        else:
            tag = f'自定义TAG:{str(tag)}'
        await bot.send(ev, str(MessageSegment.image(f'file:///{os.path.abspath(url)}') + f'\n涩图ID:{id} 来源[CQ:at,qq={str(user)}]'+ f'\n{str(tag)}'+f'\nPixivTAG:{pixiv_tag}' + f'\n上传日期{str(date)}'+f'\n支持ID、来源、TAG模糊查询哦~'))
    except CQHttpError:
        sv.logger.error(f"发送图片{id}失败")
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
                    await bot.send(ev, f'涩图收到了~id为{id}\n自定义TAG为{tag}\n稍后会自动从P站获取TAG\n删除请发送删除色图{tag}')
                else:
                    await bot.send(ev, f'涩图已经存在了哦~id为{result[0]}')
    except Exception as e:
        print("yichang",e)
        await bot.send(ev, 'wuwuwu~上传失败了~')


@sv.on_prefix(('删除涩图', '删除色图','删除男图'))
async def del_setu(bot, ev: CQEvent):
    id = str(ev.message).strip()
    user = ev['user_id']
    if not id or id=="":
        await bot.send(ev, "请在后面加上要删除的涩图序号~如果要删除非本人上传的涩图，请使用'申请删除色图'指令")
        return
    if not priv.check_priv(ev, priv.SUPERUSER):
        try:
            test_conn()
            sql="select url,user from localsetu where id = %s"%(id)
            cursor.execute(sql)
            results = cursor.fetchall()
            if not results:
                await bot.send(ev, '请检查id是否正确~')
                return 
            for row in results:
                url=row[0]
            if user != row[1]:
                await bot.send(ev, "这张涩图不是您上传的哦~如果觉得不够涩请使用'申请删除色图'指令")
                return
            else:
                os.remove(os.path.join(setu_folder, row[0]))
                sql="delete from localsetu where id = %s"%id
                cursor.execute(sql)
                conn.commit()
                await bot.send(ev, 'OvO~涩图删掉了~')
        except Exception as e:
            print("yichang",e)
            await bot.send(ev, 'QAQ~删涩图的时候出现了问题，但一定不是我的问题~')

        
    else:
        try:
            test_conn()
            sql="select url from localsetu where id = %s"%id
            cursor.execute(sql)
            results = cursor.fetchall()
            if not results:
               await bot.send(ev, '请检查id是否正确~')
               return
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

@sv.on_prefix(('反和谐'))
async def Anti_harmony(bot, ev: CQEvent):
    test_conn()
    if not str(ev.message).strip() or str(ev.message).strip()=="":
        await bot.send(ev, '请输入要反和谐的图片')
        return
    try:
        id=str(ev.message)
        sql="SELECT url,anti_url FROM bot.localsetu where id = \'%s\' ORDER BY RAND() limit 1"%(id)
        cursor.execute(sql)
        results = cursor.fetchall()
        if not results:
           await bot.send(ev, '该图片不存在~~~')
           return
    #    print(results)
        for row in results:
            name=row[0]
            url=os.path.join(setu_folder,row[0])
            anti_url=row[1]
        if anti_url and anti_url!="":
            os.remove(os.path.join(setu_folder,anti_url))
            await bot.send(ev, f'原反和谐文件已删除\\I I/')
        tem_name_url=os.path.join(setu_folder,"Anti_harmony_"+name) #临时文件，因为后面计算MD5需要的是文件而不是图片
        img=Image.open(url)
        img=image_random_one_pixel(img)
        img.save(tem_name_url,'jpeg',quality=75)
        new_MD5=image2MD5(tem_name_url)   #格式是xx.image
 #       await bot.send(ev, f'111111{tem_name_url}~')
        new_url=os.path.join(setu_folder,new_MD5)
   #     await bot.send(ev, f'222222{new_url}~')
        os.rename(tem_name_url,new_url)
        await bot.send(ev, str(MessageSegment.image(f'file:///{os.path.abspath(new_url)}')) + '\n反和谐成功~')
      #  await bot.send(ev, f'涩图{id}的TAG已更新为{tag}')
        sql="update localsetu set anti_url = \'%s\' where id = \'%s\'"%(new_MD5,id)#保存反和谐后地址
        cursor.execute(sql)
        conn.commit()
    except Exception as e:
        print("yichang",e)
        traceback.print_exc()
        await bot.send(ev, '反和谐失败了呜呜呜~')
