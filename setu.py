import os
import hjson
import random
import re
from nonebot.typing import State_T
import requests
import time
from PIL import Image
import sqlite3
import hashlib
import threading
import asyncio
from pixivpy3 import *
from PicImageSearch import SauceNAO
from nonebot.exceptions import CQHttpError
import hoshino
from hoshino import R, Service, priv
from hoshino.util import FreqLimiter, DailyNumberLimiter
from hoshino.typing import CQEvent, MessageSegment


with open('./hoshino/modules/LocalSetu/config.hjson','r', encoding='UTF-8') as json_data_file:
    config = hjson.load(json_data_file)

api_key=config['token']['sauceNAO']
refresh_token=config['token']['refresh_token']
proxy = config['proxies']['https']
verifies=config['user_list']['verifies']
db_path="./hoshino/modules/LocalSetu/LocalSetu.db" #数据库与插件同一个文件夹
proxy_on = config['proxies']['on']
_max = 100
EXCEED_NOTICE = f'您今天已经冲过{_max}次了，请明早5点后再来！'
_nlmt = DailyNumberLimiter(_max)
_flmt = FreqLimiter(5)

_REQUESTS_KWARGS = {
'proxies': {
      'https': proxy,
      }
}

class MyThread(threading.Thread):
    def __init__(self,func,args,name=''):
        threading.Thread.__init__(self)
        self.func = func
        self.name = name
        self.args = args

    def run(self):
       #print('开始执行',self.name,' 在：',ctime())
        self.res = self.func(*self.args)
        #print(self.name,'结束于：',ctime())

    def getResult(self):
        return self.res

sv = Service('LocalSetu', manage_priv=priv.SUPERUSER, enable_on_default=True, visible=False)
setu_folder = R.get('img/setu/').path
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
def test_conn():
    try:
        conn.ping()
    except:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

SETU_help="""LocalSetu涩图帮助指南：
- -kkqyxp/kkntxp[keyword]：随机发送色图/男同图，其中keyword为可选参数，支持ID、@上传者、TAG模糊查询
- -上传色/男图[TAG][图片][TAG][图片][TAG][图片]，其中TAG为可选参数，可跟多张图片
- -上传色/男图[无参数]：进入上传模式，该模式下用户发送的所有图片均视为上传，无操作20秒后自动退出
- -查看原图[ID]：可用于保存原画画质的色图
- -删除色图[ID]：删除指定ID色图，非审核人员仅可删除本人上传的色图，删除他人色图请使用'申请删除色图'
- -申请删除色图[ID]:提交色图删除申请，自动推送至审核人员
- -修改TAG[ID][TAG]：修改指定ID的自定义TAG
- -反和谐[ID]：色图被TX屏蔽时使用该指令，进行一次反和谐，后续发送色图均使用反和谐后文件
- -github链接：https://github.com/benx1n/LocalSetu 有问题欢迎提issue
=======审核人员有以下操作：
= =审核色图[上传][删除]：进入审核模式，每次发送待审核的色图，使用指令[保留][删除]后自动发送下一张，发送[退出审核]或20秒无操作自动退出
= =快速审核[ID]：快速通过指定ID的申请（默认保留）
"""
@sv.on_fullmatch(('色图帮助','setuhelp','色图帮助','setu帮助','LocalSetu'))
async def verify_setu_new(bot, ev: CQEvent):
    await bot.send(ev,SETU_help)

''' 异步下载
async def download(url, path):
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            content = await resp.read()
            with open(path, 'wb') as f:
                f.write(content)
'''
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
    img1.putpixel(pot,(random.randint(0,255),random.randint(0,255),random.randint(0,255)))
    return img1

#图片文件转为MD5
def image2MD5(filename):
    file = open(filename, "rb")
    md = hashlib.md5()
    md.update(file.read())
    res1 = md.hexdigest()
    return res1+".image"

#图片检测相似度，自动获取TAG
def verify(id,url):
    conn1= sqlite3.connect(db_path)
    cursor1 = conn1.cursor()
    start = time.time()
    verify = 0
    page = 0
    pixiv_id,index_name=get_pixiv_id(url)
    if not pixiv_id:
        sql = "update LocalSetu set verify = 1 where id = ?"
        cursor1.execute(sql,(id,))
        verify = 1
    else:
        page = re.search(r'_p(\d+)',index_name,re.X)
        pixiv_tag,pixiv_tag_t,r18,pixiv_img_url=get_pixiv_tag_url(pixiv_id,page.group(1))
        if not pixiv_tag:
            sql = "update LocalSetu set verify = 1 where id = ?"
            cursor1.execute(sql,(id,))
            verify = 1
        else:
            pixiv_img_url = pixiv_img_url.replace("i.pximg.net","i.pixiv.cat")
            sql = "update LocalSetu set pixiv_id = ?,pixiv_tag = ?,pixiv_tag_t = ?,r18 = ?,pixiv_url = ? where id = ?"
            cursor1.execute(sql,(pixiv_id,pixiv_tag,pixiv_tag_t,r18,pixiv_img_url,id))
    #lock=threading.Lock()#锁，暂时改为新建连接
    #lock.acquire()
    #lock.release()
    conn1.commit()
    return id,verify,pixiv_id,url

#获取图片pixiv_id
def get_pixiv_id(url):
    pixiv_id = 0
    similarity = 0
    saucenao = SauceNAO(api_key=api_key,**_REQUESTS_KWARGS)
    res = saucenao.search(url)
    for raw in res.raw:
        pixiv_id = raw.pixiv_id     
        similarity = raw.similarity
        index_name = raw.index_name
        if similarity > 60 and pixiv_id:
            return pixiv_id,index_name
    return 0,''

#获取图片pixiv_tag和原图url
def get_pixiv_tag_url(pixiv_id,page):
    try:
        if proxy_on:
            api = AppPixivAPI()
            api.set_accept_language('zh-cn')
            api.auth(refresh_token=refresh_token)
            json_result = api.illust_detail(pixiv_id)
            if not json_result.illust.title:
                return '','',0,''
            page_count = json_result.illust.page_count
            illust = json_result.illust.tags
            r18 = 0
            pixiv_tag = ''
            pixiv_tag_t = ''
            pixiv_img_url =''
            if illust[0]['name'] == 'R-18':
                r18 = 1
            for i in illust:
                pixiv_tag = pixiv_tag.strip()+ " "+ str(i['name']).strip('R-18')
                pixiv_tag_t = pixiv_tag_t.strip() + " "+ str(i['translated_name']).strip('None') #拼接字符串 处理带引号sql
            pixiv_tag = pixiv_tag.strip()
            pixiv_tag_t = pixiv_tag_t.strip()
            if page_count == 1:
                pixiv_img_url=json_result.illust.meta_single_page['original_image_url']
            else:
                pixiv_img_url=json_result.illust.meta_pages[int(page)]['image_urls']['original']
            return pixiv_tag,pixiv_tag_t,r18,pixiv_img_url
        else:
            return '','',0,''
    except Exception as e:
        return '','',0,''

@sv.on_prefix(('kkqyxp','看看群友xp','看看群友性癖','kkntxp','看看男同xp','看看男同性癖'))
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
    id1=0
    searchtag = str(ev.message).strip()
    if not searchtag or searchtag=="":
        id1=1
    elif ev.message[0].type == 'at':
        id1 = 2
        user = int(ev.message[0].data['qq'])
    try:
        test_conn()
        is_man = 0
        if ev['prefix'] == ('kkntxp'or '看看男同xp' or '看看男同性癖'):
            is_man = 1
        if id1==0:#带tag
            if searchtag.isdigit(): #id
                sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify FROM LocalSetu where man = ? AND id = ? ORDER BY random() limit 1"
                cursor.execute(sql,(is_man,searchtag))
            else:   #tag
                sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify FROM LocalSetu where man = ? AND (tag like ? OR pixiv_tag like ? OR pixiv_tag_t like ?) ORDER BY random() limit 1"
                searchtag = '%'+searchtag+'%'
                cursor.execute(sql,(is_man,searchtag,searchtag,searchtag))
        elif id1==1:#全随机
            sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify FROM LocalSetu where man = ? ORDER BY random() limit 1"
            cursor.execute(sql,(is_man,))
        elif id1==2:#指定人
            sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify from LocalSetu where man = ? AND user = ? ORDER BY random() limit 1"
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
        verify = result[9]
        if result[2]:
            url = anti_url
        if verify:
            await bot.send(ev,"该图正在等待审核，暂不支持查看~")
            return
        if tag:
            tag = f'当前TAG为空，您可以发送修改TAG{id}进行编辑~'
        else:
            tag = f'自定义TAG:{str(tag)}'
        if pixiv_id :
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

@sv.on_prefix(('查看原图','看看原图','看看大图','查看大图'))
async def get_original_setu(bot, ev: CQEvent):
    id = str(ev.message).strip()
    if not id or id=="" or not id.isdigit():
        await bot.send(ev, "请在后面加上要查看的涩图序号~")
        return
    try:
        test_conn()
        sql="SELECT pixiv_url,verify,pixiv_name,pixiv_id,url FROM LocalSetu where id = ?"
        cursor.execute(sql,(id,))
        results = cursor.fetchone()
        if not results:
            await bot.send(ev, '请检查id是否正确~')
            return
        elif results[1]:
            await bot.send(ev,"该涩图正在等待审核，暂不支持查看~")
            return
        pixiv_img_url = results[0]
        pixiv_name = results[2]
        pixiv_id = results[3]
        if not pixiv_name:
            await bot.send(ev, '本地没有找到记录，正在尝试获取原画')
            pixiv_id,index_name=get_pixiv_id(os.path.join(setu_folder,results[4]))
            if not pixiv_id:
                await bot.send(ev, '获取失败了~')
                return
            else:
                page = re.search(r'_p(\d+)',index_name,re.X)
                pixiv_tag,pixiv_tag_t,r18,pixiv_img_url=get_pixiv_tag_url(pixiv_id,page.group(1))
                if not pixiv_tag:
                    await bot.send(ev, '无法获取原画，该原画可能已被删除')
                    return
                else:
                    pixiv_img_url = pixiv_img_url.replace("i.pximg.net","i.pixiv.cat")
                    pixiv_name = os.path.split(pixiv_img_url)[1]
                    new_download(pixiv_img_url,os.path.join(setu_folder,pixiv_name))
                    sql = "update LocalSetu set pixiv_id = ?,pixiv_tag = ?,pixiv_tag_t = ?,r18 = ?,pixiv_url = ?,pixiv_name = ? where id = ?"
                    cursor.execute(sql,(pixiv_id,pixiv_tag,pixiv_tag_t,r18,pixiv_img_url,pixiv_name,id))
                    conn.commit()
        url=os.path.join(setu_folder,pixiv_name)
        await bot.send(ev,MessageSegment.image(f'file:///{os.path.abspath(url)}') + f'\n原图链接：https://pixiv.net/i/{pixiv_id}' + f'\n反代链接:{pixiv_img_url}')
    except CQHttpError:
        sv.logger.error(f"发送图片{id}失败")
        try:
            await bot.send(ev, 'T T涩图不知道为什么发不出去勒...tu')
        except:
            pass

class load_images:
    def __init__(self):
        self.group_id=""     #开启审核的群id
        self.user_id=""      #上传的人的id
        self.switch=0   #当前是否处于审核状态 0 不处于 1处于
        self.flag=0     #执行次数
        self.is_man=0   #是否男图
li=load_images()

@sv.on_message()
async def load_setu_in_message(bot, ev:CQEvent):
    if li.group_id!=ev['group_id'] or not li.switch :   #判断开启色图模式的和发图的是不是同一个群，以及是否开启收图模式
        return
    if li.user_id!=ev['user_id']:#判断是不是同一个人
        return
    if not (str(ev.message).find("[CQ:image")+1):  #判断收到的信息是否为图片，不是就退出
        return
    await load_setu(bot,ev)
    li.flag=0

@sv.on_prefix(('上传色图','上传男图'))
async def give_setu(bot, ev:CQEvent):
    try:
        li.is_man = 0
        if ev['prefix'] == '上传男图': 
            li.is_man = 1
        if not str(ev.message).strip() or str(ev.message).strip()=="":
            if li.switch:                                                #当前已经开启
                await bot.send(ev, '当前有人在上传~请稍等片刻~')
                return
            await bot.send(ev, '发涩图发涩图~开启收图模式~')
            li.switch=1
            li.flag=0
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
        await bot.send(ev, 'wuwuwu~上传失败了~')

async def load_setu(bot,ev):
    try:
        test_conn()
        tag = ""
        is_man = li.is_man
        threads1 = []
        threads2 = []
        for seg in ev.message:
            if seg.type == 'text':
                tag=str(seg).strip()
            elif seg.type == 'image':
                img_url = seg.data['url']
                setu_name = str(seg.data['file'])
                user = str(ev['user_id'])
                sql="SELECT id FROM LocalSetu where url = ?"
                cursor.execute(sql,(setu_name,))
                result = cursor.fetchone()
                if not result:
                    sql="INSERT OR IGNORE INTO LocalSetu (id,url,user,date,tag,man) VALUES (NULL,?,?,datetime('now'),?,?)"
                    cursor.execute(sql,(setu_name,user,tag,is_man))
                    id=cursor.lastrowid
                    conn.commit()
                    threads1.append(MyThread(new_download,(img_url, os.path.join(setu_folder,setu_name)),verify.__name__))
                    await bot.send(ev, f'[CQ:image,file={img_url}]'+f'涩图收到了~id为{id}\n自定义TAG为{tag}\n稍后会自动从P站获取TAG\n删除请发送删除色图{id}')
                    threads2.append(MyThread(verify,(id,img_url),verify.__name__))
                else:
                    await bot.send(ev, f'涩图已经存在了哦~id为{result[0]}')
        for t in threads1:
            t.setDaemon(True)
            t.start()
        if proxy_on:
            for t in threads2:
                t.setDaemon(True)
                t.start()
            for t in threads2:
                t.join()
                id,verifynum,pixiv_id,img_url= t.getResult()
                if not verifynum:
                    await bot.send(ev, f'id:{id}上传成功，自动审核通过\n已自动为您获取原图PixivID:{pixiv_id}\n'+f"发送'查看原图+ID'即可")
                else:
                    await bot.send(ev, f'id:{id}上传成功，但没完全成功，请等待人工审核哦~[CQ:at,qq={str(user)}]')
                    for ves in verifies:
                        await bot.send_private_msg(self_id=ev.self_id, user_id=int(ves), message=f'有新的上传申请,id:{id}'+f'[CQ:image,file={img_url}]')
        else:
            await bot.send(ev, f'由于您未开启代理，无法自动获取色图信息')
    except Exception as e:
        await bot.send(ev, 'wuwuwu~上传出现了问题~')

@sv.on_prefix(('删除涩图', '删除色图','删除男图'))
async def del_setu(bot, ev: CQEvent):
    id = str(ev.message).strip()
    user = ev['user_id']
    if not id or id=="" or not id.isdigit():
        await bot.send(ev, "请在后面加上要删除的涩图序号~如果要删除非本人上传的涩图，请使用'申请删除色图'指令")
        return
    if int(user) not in verifies:
        try:
            test_conn()
            sql="select url,user from LocalSetu where id = ?"
            cursor.execute(sql,(id,))
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
                    os.remove(os.path.join(setu_folder, url))
                    sql="delete from LocalSetu where id = ?"
                    cursor.execute(sql,(id,))
                    conn.commit()
                    await bot.send(ev, 'OvO~涩图删掉了~')
        except Exception as e:
            await bot.send(ev, 'QAQ~删涩图的时候出现了问题，但一定不是我的问题~')
    else:
        try:
            test_conn()
            sql="select url from LocalSetu where id = ?"
            cursor.execute(sql,(id,))
            results = cursor.fetchall()
            if not results:
                await bot.send(ev, '请检查id是否正确~')
                return
            for row in results:
                url=row[0]
            os.remove(os.path.join(setu_folder, url))
            sql="delete from LocalSetu where id = ?"
            cursor.execute(sql,(id,))
            conn.commit()
            await bot.send(ev, 'OvO~涩图删掉了~')
        except Exception as e:
            await bot.send(ev, 'QAQ~删涩图的时候出现了问题，但一定不是我的问题~')

@sv.on_prefix(('修改TAG','修改tag'))
async def modify_tag(bot, ev: CQEvent):
    test_conn()
    if not str(ev.message).strip() or str(ev.message).strip()=="":
        await bot.send(ev, '请在指令后添加ID和TAG哦~以空格区分')
        return
    try:
        id,tag=str(ev.message).split(' ', 1 )
        sql="update LocalSetu set tag = ? where id = ?"
        cursor.execute(sql,(tag,id))
        conn.commit()
        await bot.send(ev, f'涩图{id}的TAG已更新为{tag}')
    except Exception as e:
        await bot.send(ev, '请在指令后添加ID和TAG哦~以空格区分')

@sv.on_prefix(('反和谐'))
async def Anti_harmony(bot, ev: CQEvent):
    test_conn()
    if not str(ev.message).strip() or str(ev.message).strip()=="":
        await bot.send(ev, '请输入要反和谐的图片')
        return
    try:
        id=str(ev.message)
        sql="SELECT url,anti_url FROM LocalSetu where id =? ORDER BY random() limit 1"
        cursor.execute(sql,(id,))
        results = cursor.fetchall()
        if not results:
           await bot.send(ev, '该图片不存在~~~')
           return
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
        new_url=os.path.join(setu_folder,new_MD5)
        os.rename(tem_name_url,new_url)
        await bot.send(ev, str(MessageSegment.image(f'file:///{os.path.abspath(new_url)}')) + '\n反和谐成功~')
        sql="update LocalSetu set anti_url = ? where id = ?"#保存反和谐后地址
        cursor.execute(sql,(new_MD5,id))
        conn.commit()
    except Exception as e:
        await bot.send(ev, '反和谐失败了呜呜呜~')

@sv.on_prefix(('申请删除色图'))
async def apply_delete(bot, ev: CQEvent):
    id = str(ev.message).strip()
    if not id or id=="":
        await bot.send(ev, "请在后面加上要申请删除的涩图序号~")
        return
    try:
        test_conn()
        sql="select verify,url from LocalSetu where id = ?"
        cursor.execute(sql,(id,))
        results = cursor.fetchone()
        if not results:
           await bot.send(ev, '请检查id是否正确~')
           return
        verify=results[0]
        url = os.path.join(setu_folder,results[1])
        if verify:
            await bot.send(ev, '该图正在审核哦~')
            return
        sql="update LocalSetu set verify = 2 where id = ?"
        cursor.execute(sql,(id,))
        conn.commit()
        await bot.send(ev, '提交审核成功，请耐心等待哦~')
        for ves in verifies:
            await bot.send_private_msg(self_id=ev.self_id, user_id=int(ves),message=f'有新的删除申请,id:{id}'+str(MessageSegment.image(f'file:///{os.path.abspath(url)}')))
    except Exception as e:
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
    if int(ev["user_id"]) not in verifies:
        await bot.send(ev, '你谁啊你，不是管理员没资格审核色图哦~')
        return
    if ev['prefix'] == '审核色图上传':
        sql="select url,user,date,id from LocalSetu where verify=1 order by random() limit 1"
    elif ev['prefix'] == '审核色图删除':
        sql="select url,user,date,id from LocalSetu where verify=2 order by random() limit 1"
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
        await bot.send(ev, 'QAQ~审核的时候出现了问题，但一定不是我的问题~')

@sv.on_fullmatch(('保留','删除','退出审核'))
async def verify_complete(bot, ev: CQEvent):
    if not ve.switch and int(ev["user_id"]) not in verifies:
        return
    try:
        test_conn()
        if ev['prefix'] == '保留':
            sql="update LocalSetu set verify=0 where id = ?"
            cursor.execute(sql,(ve.id,))
            conn.commit()
            await bot.send(ev, '当前图片审核通过'+str(MessageSegment.image(f'file:///{os.path.abspath(ve.url)}'))+f'id为{ve.id}')
        elif ev['prefix'] == '删除':
            os.remove(ve.url)
            sql="delete from LocalSetu where id = ?"
            cursor.execute(sql,(ve.id,))
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
    id = str(ev.message).strip()
    user = ev['user_id']
    if int(user) not in verifies:
        await bot.send(ev,'你谁啊你，不是管理员没资格审核色图哦~')
        return
    if not id:
        await bot.send(ev, "请在后面加上要通过的涩图序号f~")
        return
    try:
        test_conn()
        sql="update LocalSetu set verify=0 where id = ?"
        cursor.execute(sql,(id,))
        conn.commit()
        await bot.send(ev, f'色图{id}审核通过')
    except Exception as e:
        await bot.send(ev, "出了点小问题，但一定不是我的问题~")
