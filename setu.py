import os
import json
import random
import re
from sys import flags
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
import threading
import asyncio
from pixivpy3 import *
from PicImageSearch import SauceNAO
from time import ctime,sleep
from nonebot.exceptions import CQHttpError
import hoshino
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
api_key=config['api']['sauceNAO']
refresh_token=config['api']['refresh_token']

_max = 100
EXCEED_NOTICE = f'您今天已经冲过{_max}次了，请明早5点后再来！'
_nlmt = DailyNumberLimiter(_max)
_flmt = FreqLimiter(5)

_REQUESTS_KWARGS = {
'proxies': {
      'https': 'http://127.0.0.1:7890',
      }
}

class MyThread(threading.Thread):
    def __init__(self,func,args,name=''):
        threading.Thread.__init__(self)
        self.func = func
        self.name = name
        self.args = args

    def run(self):
        print('开始执行',self.name,' 在：',ctime())
        self.res = self.func(*self.args)
        print(self.name,'结束于：',ctime())

    def getResult(self):
        return self.res


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
# 异步下载
async def download(url, path):
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            content = await resp.read()
            with open(path, 'wb') as f:
                f.write(content)

def new_download(url, path):
    img_file = requests.get(url)
    with open(path, 'wb') as f:
        f.write(img_file.content)
    return url
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

#图片检测相似度，自动获取TAG
def verify(id,url):
    conn1= pymysql.connect(host=host,user=user,password=password,database=database,charset='utf8',autocommit = 1)
    cursor1 = conn1.cursor()
    start = time.time()
    verify = 0
    pixiv_id,similarity=get_pixiv_id(url)
    if pixiv_id == 0 or pixiv_id == '' or not pixiv_id:
        sql = "update localsetu set verify = 1 where id = %s"
        cursor1.execute(sql,(id))
        verify = 1
    else:
        pixiv_tag,pixiv_tag_t,r18=get_pixiv_tag(pixiv_id)
        sql = "update localsetu set pixiv_id = %s,pixiv_tag = %s,pixiv_tag_t = %s,r18 = %s where id = %s"%(pixiv_id,pixiv_tag,pixiv_tag_t,r18,id)
        cursor1.execute(sql)
    #lock=threading.Lock()#锁，暂时改为新建连接
    #lock.acquire()
        
    #lock.release()
    print("usetime:%f s"%(time.time()-start))
    return id,verify,pixiv_id,url

#获取图片pixiv_id
def get_pixiv_id(url):
    pixiv_id = 0
    similarity = 0
    saucenao = SauceNAO(api_key=api_key,**_REQUESTS_KWARGS)
    #print('seru138  url:',url)
    res = saucenao.search(url)
    #print('res',res)
    #print(res.raw[0])
    pixiv_id = res.raw[0].pixiv_id
    #print(pixiv_id)
    similarity = res.raw[0].similarity
    #print(similarity)
    if similarity < 60 or pixiv_id == '' or not pixiv_id:
        print(res.raw[0].similarity)
        pixiv_id = 0
    return pixiv_id,similarity

#获取图片pixiv_tag
def get_pixiv_tag(pixiv_id):
    try:
        api = AppPixivAPI()
        api.set_accept_language('zh-cn')
        api.auth(refresh_token=refresh_token)
        json_result = api.illust_detail(pixiv_id)
        illust = json_result.illust.tags
        r18 = 0
        pixiv_tag = ''
        pixiv_tag_t = ''
        if illust[0]['name'] == 'R-18':
            r18 = 1
        for i in illust:
            pixiv_tag = pixiv_tag.strip()+ " "+ str(i['name']).strip('R-18').replace("'","\\'")
            pixiv_tag_t = pixiv_tag_t.strip() + " "+ str(i['translated_name']).strip('None').replace("'","\\'") #拼接字符串 处理带引号sql
        pixiv_tag = pixiv_tag.strip()
        pixiv_tag_t = pixiv_tag_t.strip()
        #print(pixiv_tag_t)
        return pixiv_tag,pixiv_tag_t,r18
    except Exception as e:
        print("yichang1",e)
        return '','',0

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
                sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,verify FROM bot.localsetu where man = %s AND id = %s ORDER BY RAND() limit 1"
                cursor.execute(sql,(is_man,searchtag))
            else:   #tag
                sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,verify FROM bot.localsetu where man = %s AND (tag like %s OR pixiv_tag like %s OR pixiv_tag_t like %s) ORDER BY RAND() limit 1"
                searchtag = '%'+searchtag+'%'
                cursor.execute(sql,(is_man,searchtag,searchtag,searchtag))
        if id1==1:#全随机
            sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,verify FROM bot.localsetu where man = %s ORDER BY RAND() limit 1"
            cursor.execute(sql,(is_man))
        elif id1==2:#指定人
            sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,verify from localsetu where man = %s AND user = %s ORDER BY RAND() limit 1"
            cursor.execute(sql,(is_man,str(user)))
        conn.commit()
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
        pixiv_id = result[7]
        verify = result[8]
        if result[2]:
            url = anti_url
        if verify:
            await bot.send(ev,"该图正在等待审核，暂不支持查看~")
            return
        if tag:
            tag = f'当前TAG为空，您可以发送修改TAG{id}进行编辑~'
        else:
            tag = f'自定义TAG:{str(tag)}'
        if pixiv_id != 0 :
            pixiv_url = "https://pixiv.net/i/"+ str(pixiv_id)
            await bot.send(ev, str(MessageSegment.image(f'file:///{os.path.abspath(url)}') + f'\n涩图ID:{id} 来源[CQ:at,qq={str(user)}]'+ f'\n{str(tag)}'+f'\nPixivTAG:{pixiv_tag}' +f'\n{pixiv_url}' +f'\n支持ID、来源、TAG模糊查询哦~'))
        else:
            await bot.send(ev, str(MessageSegment.image(f'file:///{os.path.abspath(url)}') + f'\n涩图ID:{id} 来源[CQ:at,qq={str(user)}]'+ f'\n{str(tag)}'+f'\nPixivTAG:{pixiv_tag}' +f'\n支持ID、来源、TAG模糊查询哦~'))
    except CQHttpError:
        sv.logger.error(f"发送图片{id}失败")
        try:
            await bot.send(ev, 'T T涩图不知道为什么发不出去勒...tu')
        except:
            pass

'''旧上传方法，已弃用
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
                    await bot.send(ev, f'涩图收到了~id为{id}\n自定义TAG为{tag}\n稍后会自动从P站获取TAG\n删除请发送删除色图{id}')
                else:
                    await bot.send(ev, f'涩图已经存在了哦~id为{result[0]}')
    except Exception as e:
        print("yichang",e)
        await bot.send(ev, 'wuwuwu~上传失败了~')
'''

class load_images:
    def __init__(self):
        self.group_id=""     #开启审核的群id
        self.user_id=""      #上传的人的id
        self.switch=0   #当前是否处于审核状态 0 不处于 1处于
        self.flag=0 #执行次数
        self.is_man=0
li=load_images()

async def load_setu(bot,ev):
    try:
  #      await bot.send(ev, f'ev:{ev}')
        test_conn()
        tag = ""
        is_man = li.is_man
        tasks1=[]
        threads1 = []
        threads2 = []
        for i,seg in enumerate(ev.message):
            if seg.type == 'text':
                tag=str(seg).strip()
            elif seg.type == 'image':
                img_url = seg.data['url']
                setu_name = str(seg.data['file'])
                user = str(ev['user_id'])
                sql="SELECT id FROM localsetu where url = %s"
                cursor.execute(sql,(setu_name))
                result = cursor.fetchone()
                if not result:
                    sql="INSERT IGNORE INTO localsetu (id,url,user,date,tag,man) VALUES (NULL,%s,%s,NOW(),%s,%s)"
                    cursor.execute(sql,(setu_name,user,tag,is_man))
                    id=cursor.lastrowid
                    conn.commit()
                    threads1.append(MyThread(new_download,(img_url, os.path.join(setu_folder,setu_name)),verify.__name__))
                    await bot.send(ev, f'涩图收到了~id为{id}\n自定义TAG为{tag}\n稍后会自动从P站获取TAG\n删除请发送删除色图{id}')
                    threads2.append(MyThread(verify,(id,img_url),verify.__name__))
                else:
                    await bot.send(ev, f'涩图已经存在了哦~id为{result[0]}')
        for t in threads1:
            t.setDaemon(True)
            t.start()      
        for t in threads2:
            t.setDaemon(True)
            t.start()
        for t in threads2:
            t.join()
            print(t.getResult())
            print(type(t.getResult()))
            id,verifynum,pixiv_id,img_url= t.getResult()
            if not verifynum:
                await bot.send(ev, f'id:{id}上传成功，自动审核通过\nPixivID:{pixiv_id}')
            else:
                await bot.send(ev, f'id:{id}上传成功，但没完全成功，请等待人工审核哦~[CQ:at,qq={str(user)}]')
                await bot.send_private_msg(self_id=ev.self_id, user_id=1119809439, message=f'有新的上传申请,id:{id}'+f'[CQ:image,file={img_url}]')
                await bot.send_private_msg(self_id=ev.self_id, user_id=635040951, message=f'有新的上传申请,id:{id}'+f'[CQ:image,file={img_url}]')
    except Exception as e:
        print("yichang",e)
        traceback.print_exc()
        await bot.send(ev, 'wuwuwu~上传出现了问题~')

@sv.on_message()
async def load_setu_in_message(bot, ev:CQEvent):
    if li.group_id!=ev['group_id'] or not li.switch or li.user_id!=ev['user_id']:
        return
  #  await bot.send(ev, f'ev:{ev}')
    await load_setu(bot,ev)
    li.flag=0

@sv.on_prefix(('上传色图','上传男图'))
async def give_setu(bot, ev:CQEvent):
    try:
        print(ev)
        li.is_man = 0
        if ev['prefix'] == '上传男图':  #这里需要研究一下
            li.is_man = 1
        if not str(ev.message).strip() or str(ev.message).strip()=="":
            if li.switch:
                await bot.send(ev, '当前有人在上传~请稍等片刻~')
            await bot.send(ev, '发涩图发涩图~开启收图模式~')
            li.switch=1
            li.group_id=ev['group_id']
            li.user_id=ev['user_id']
            while li.flag<40:
                li.flag = li.flag + 1
                await asyncio.sleep(0.5)
            await bot.send(ev, '溜了溜了~')
            li.switch=0
            return
        await load_setu(bot,ev)
    except Exception as e:
        print("yichang",e)
        await bot.send(ev, 'wuwuwu~上传失败了~')

@sv.on_prefix(('删除涩图', '删除色图','删除男图'))
async def del_setu(bot, ev: CQEvent):
    id = str(ev.message).strip()
    user = ev['user_id']
    if not id or id=="" or not id.isdigit():
        await bot.send(ev, "请在后面加上要删除的涩图序号~如果要删除非本人上传的涩图，请使用'申请删除色图'指令")
        return
    if not priv.check_priv(ev, priv.SUPERUSER):
        try:
            test_conn()
            sql="select url,user from localsetu where id = %s"
            cursor.execute(sql,((id)))
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
                sql="delete from localsetu where id = %s"
                cursor.execute(sql,(id))
                conn.commit()
                await bot.send(ev, 'OvO~涩图删掉了~')
        except Exception as e:
            print("yichang",e)
            await bot.send(ev, 'QAQ~删涩图的时候出现了问题，但一定不是我的问题~')
    else:
        try:
            test_conn()
            sql="select url from localsetu where id = %s"
            cursor.execute(sql,(id))
            results = cursor.fetchall()
            if not results:
               await bot.send(ev, '请检查id是否正确~')
               return
            for row in results:
                url=row[0]
            os.remove(os.path.join(setu_folder, row[0]))
            sql="delete from localsetu where id = %s"
            cursor.execute(sql,(id))
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
        sql="update localsetu set tag = %s where id = %s"
        cursor.execute(sql,(tag,id))
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
        sql="SELECT url,anti_url FROM bot.localsetu where id =%s ORDER BY RAND() limit 1"
        cursor.execute(sql,(id))
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
        sql="update localsetu set anti_url = %s where id = %s"#保存反和谐后地址
        cursor.execute(sql,(new_MD5,id))
        conn.commit()
    except Exception as e:
        print("yichang",e)
        traceback.print_exc()
        await bot.send(ev, '反和谐失败了呜呜呜~')

@sv.on_prefix(('申请删除色图'))
async def apply_delete(bot, ev: CQEvent):
    id = str(ev.message).strip()
    user = ev['user_id']
    if not id or id=="":
        await bot.send(ev, "请在后面加上要申请删除的涩图序号~")
        return
    try:
        test_conn()
        sql="select verify,url from localsetu where id = %s"
        cursor.execute(sql,(id))
        results = cursor.fetchone()
        if not results:
           await bot.send(ev, '请检查id是否正确~')
           return
        verify=results[0]
        url = os.path.join(setu_folder,results[1])
        if verify:
            await bot.send(ev, '该图正在审核哦~')
            return
        sql="update localsetu set verify = 2 where id = %s"
        cursor.execute(sql,(id))
        conn.commit()
        await bot.send(ev, '提交审核成功，请耐心等待哦~')
        print(type(hoshino.config.SUPERUSERS[0]))
        await bot.send_private_msg(self_id=ev.self_id, user_id=1119809439,message=f'有新的删除申请,id:{id}'+str(MessageSegment.image(f'file:///{os.path.abspath(url)}')))
        await bot.send_private_msg(self_id=ev.self_id, user_id=635040951,message=f'有新的删除申请,id:{id}'+str(MessageSegment.image(f'file:///{os.path.abspath(url)}')))
    except Exception as e:
        print("yichang",e)
        await bot.send(ev, 'QAQ~出了点小问题,说不定过一会儿就能恢复')

class Verify:
    def __init__(self):
        self.url=""     #审核的色图url
        self.switch=0   #当前是否处于审核状态 0 不处于 1处于
        self.id=-1     #审核的色图id
        self.sql_state=0 #是否执行过sql
        self.flag=0 #执行次数
ve=Verify()

@sv.on_fullmatch(('审核色图上传','审核色图删除'))
async def verify_setu(bot, ev: CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        await bot.send(ev, '你谁啊你，不是管理员没资格审核色图哦~')
        return
    if ev['prefix'] == '审核色图上传':
        sql="select url,user,date,id from localsetu where verify=1 order by rand() limit 1"
    elif ev['prefix'] == '审核色图删除':
        sql="select url,user,date,id from localsetu where verify=2 order by rand() limit 1"
    ve.sql_state,ve.flag=0,0
    try:
        while ve.flag < 40:
            ve.flag = ve.flag + 1
            if not ve.sql_state:
                test_conn()
                cursor.execute(sql)
                results = cursor.fetchone()
                if not results:
                    await bot.send(ev, '当前没有要审核图片哦，摸鱼大胜利~')
                    return                                 
                ve.url=os.path.join(setu_folder,results[0])
                user=results[1]
                date=results[2]
                ve.id=results[3]
                await bot.send(ev, '当前审核的图片为'+str(MessageSegment.image(f'file:///{os.path.abspath(ve.url)}'))+f'ID：{ve.id}\n来源为[CQ:at,qq={str(user)}]\n上传时间:{date}')
                ve.sql_state,ve.switch = 1,1
            await asyncio.sleep(0.5)
        await bot.send(ev, '20秒过去了，审核结束~')
        return
    except Exception as e:
        print("yichang",e)
    await bot.send(ev, 'QAQ~审核的时候出现了问题，但一定不是我的问题~')

@sv.on_fullmatch(('保留','删除','退出审核'))
async def verify_complete(bot, ev: CQEvent):
    if not ve.switch:
        return
    try:
        test_conn()
        if ev['prefix'] == '保留':
            sql="update localsetu set verify=0 where id = %s"
            cursor.execute(sql,(ve.id))
            conn.commit()
            await bot.send(ev, '当前图片审核通过'+str(MessageSegment.image(f'file:///{os.path.abspath(ve.url)}'))+f'id为{ve.id}')
        elif ev['prefix'] == '删除':
            os.remove(ve.url)
            sql="delete from localsetu where id = %s"
            cursor.execute(sql,(ve.id))
            conn.commit()
            await bot.send(ev, 'OvO~不合格的涩图删掉了~')
        elif ev['prefix'] == '退出审核':
            ve.flag = 40
            return 
        ve.switch,ve.flag,ve.sql_state= 0,0,0
    except:
        await bot.send(ev, '出了点小问题，其实我觉得这图片挺涩的~')
    return

@sv.on_prefix('快速审核')
async def quick_verify(bot, ev:CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        await bot.send(ev,'你谁啊你，不是管理员没资格审核色图哦~')
        return
    id = str(ev.message).strip()
    user = ev['user_id']
    if not id:
        await bot.send(ev, "请在后面加上要通过的涩图序号f~")
        return
    try:
        test_conn()
        sql="update localsetu set verify=0 where id = %s"
        cursor.execute(sql,((id)))
        conn.commit()
        await bot.send(ev, f'色图{id}审核通过')
    except Exception as e:
        await bot.send(ev, "出了点小问题，但一定不是我的问题~")
        print("yichang",e)


''' 旧异步方法 弃用
@sv.on_prefix(('色图检测'))
async def give_setu(bot, ev:CQEvent):
    try:
        print(ev)
        test_conn()
        if not str(ev.message).strip() or str(ev.message).strip()=="":
            await bot.send(ev, '发涩图发涩图~')
            return
        tag = ""
        is_man = 0
        tasks1=[]
        tasks2=[]
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
                    sql="INSERT IGNORE INTO localsetu (id,url,user,date,tag,man) VALUES (NULL,\'%s\',%s,NOW(),\'%s\',%s)"%(setu_name,str(ev['user_id']),tag,is_man)
                    cursor.execute(sql)
                    id=cursor.lastrowid
                    conn.commit()
                    tasks1.append(download(img_url, os.path.join(setu_folder,setu_name)))
                    await bot.send(ev, f'涩图收到了~id为{id}\n自定义TAG为{tag}\n稍后会自动从P站获取TAG\n删除请发送删除色图{id}')
                    tasks2.append(get_pixiv_id(img_url))
                else:
                    await bot.send(ev, f'涩图已经存在了哦~id为{result[0]}')
        await asyncio.gather(*tasks1)
        results2 = await asyncio.gather(*tasks2)
        for result in results2:
            print(result)
            await bot.send(ev, f'涩图收到了~id为{result[0]}\nPixivTAG:{result[3]}\n删除请发送删除色图{result[0]}')

    except Exception as e:
        print("色图检测异常：",e)
        await bot.send(ev, 'wuwuwu~上传失败了~')


 id = 716
        pixiv_tag=''
        pixiv_tag_t=''
        r18=0
        print(id)
        try:
            pixiv_id= get_pixiv_id(url)
            print(pixiv_id)
            try:
                pixiv_tag,pixiv_tag_t,r18=get_pixiv_tag(pixiv_id)
            except Exception as e:
                print("yichang2",e)
                continue
            pixiv_tag_t = pixiv_tag_t.strip('None')
        except Exception as e:
            print("yichang3",e)
            continue
        sql="update localsetu set pixiv_id = %s , pixiv_tag = \'%s\' , pixiv_tag_t = \'%s\' , r18 = %s where id = %s"%(pixiv_id,pixiv_tag,pixiv_tag_t,r18,id)
        cursor.execute(sql)
        conn.commit()
    await bot.send(ev,pixiv_tag)
    await bot.send(ev,pixiv_tag_t)
    

@sv.on_fullmatch(('开发审核色图'))
async def verify_setu_new(bot, ev: CQEvent):
    if not priv.check_priv(ev, priv.SUPERUSER):
        await bot.send(ev, '你谁啊你，不是管理员没资格审核色图哦~')
        return
    else:
        ve.state=1
        try:
            while ve.state:
                ve.state=0
                test_conn()
                sql="select url,user,date,id from localsetu where verify=1 order by rand() limit 1"
                cursor.execute(sql)
                results = cursor.fetchall()
                if not results:
                    await bot.send(ev, '当前没有要审核图片哦，摸鱼大胜利~')
                    return 
                ve.switch=1
                for row in results:
                    url=os.path.join(setu_folder,row[0])
                    user=row[1]
                    date=row[2]
                    id=row[3]
                ve.url=url
                ve.id=id
                await bot.send(ev, '当前审核的图片为'+str(MessageSegment.image(f'file:///{os.path.abspath(url)}'))+f'ID：{id}\n来源为[CQ:at,qq={str(user)}]\n上传时间:{date}')
                await asyncio.sleep(20)
                await bot.send(ev, '二十秒过去了，你爬吧~')
                ve.switch=0
        except Exception as e:
            print("yichang",e)
            await bot.send(ev, 'QAQ~审核的时候出现了问题，但一定不是我的问题~')
    await bot.send(ev, '审核结束~')
    return
异步+多线程方法
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
        tasks1=[]
        threads = []
        if ev['prefix'] == '上传男图':
            is_man = 1
        for i,seg in enumerate(ev.message):
            if seg.type == 'text':
                tag=str(seg).strip()
            elif seg.type == 'image':
                img_url = seg.data['url']
                setu_name = seg.data['file']
                user = str(ev['user_id'])
                sql="SELECT id FROM localsetu where url = '%s'"%str(seg.data['file'])
                cursor.execute(sql)
                result = cursor.fetchone()
                if not result:
                    sql="INSERT IGNORE INTO localsetu (id,url,user,date,tag,man) VALUES (NULL,\'%s\',%s,NOW(),\'%s\',%s)"%(setu_name,user,tag,is_man)
                    cursor.execute(sql)
                    id=cursor.lastrowid
                    conn.commit()
                    tasks1.append(download(img_url, os.path.join(setu_folder,setu_name)))
                    tasks1.append(bot.send(ev, f'涩图收到了~id为{id}\n自定义TAG为{tag}\n稍后会自动从P站获取TAG\n删除请发送删除色图{id}'))
                    threads.append(MyThread(verify,(id,img_url),verify.__name__))
                else:
                    await bot.send(ev, f'涩图已经存在了哦~id为{result[0]}')
        start2 = time.time()
        await asyncio.gather(*tasks1)
        for t in threads:
            t.setDaemon(True)
            t.start()
        for t in threads:
            t.join()
            print(t.getResult())
            id,verifynum,pixiv_id,img_url= t.getResult()
            if not verifynum:
                await bot.send(ev, f'id:{id}上传成功，自动审核通过\nPixivID:{pixiv_id}')
            else:
                await bot.send(ev, f'id:{id}上传成功，但没完全成功，请等待人工审核哦~[CQ:at,qq={str(user)}]')
                await bot.send_private_msg(self_id=ev.self_id, user_id=1119809439, message=f'有新的上传申请,id:{id}'+f'[CQ:image,file={img_url}]')
                await bot.send_private_msg(self_id=ev.self_id, user_id=635040951, message=f'有新的上传申请,id:{id}'+f'[CQ:image,file={img_url}]')
        print("usetime22222222222222222222222222:%f s"%(time.time()-start2))
    except Exception as e:
        print("yichang",e)
        await bot.send(ev, 'wuwuwu~上传失败了~')
    '''