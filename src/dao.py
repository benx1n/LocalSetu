import sqlite3
from pathlib import Path


dir_path = Path(__file__).parent
db_path = dir_path.parent/'LocalSetu.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def test_conn():
    try:
        conn.ping()
    except:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

class getImgDao:
    def __init__(self):
        test_conn()
        
    def get_local_image_random(self, is_man):
        """随机图片
        id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify
        """
        sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify FROM LocalSetu where man = ? AND verify = 0 ORDER BY random() limit 1"
        cursor.execute(sql,(is_man,))
        conn.commit()
        return cursor.fetchone()
    
    def get_local_image_user(self, is_man,user):  
        """根据用户查找图片
        id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify
        """
        sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify from LocalSetu where man = ? AND user = ? AND verify = 0 ORDER BY random() limit 1"
        cursor.execute(sql,(is_man,str(user)))
        conn.commit()
        return cursor.fetchone()
    
    def get_local_image_ID(self, is_man,id):
        """根据ID查找图片
        id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify
        """
        test_conn()
        sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify FROM LocalSetu where man = ? AND id = ? ORDER BY random() limit 1"
        cursor.execute(sql,(is_man,id))
        conn.commit()
        return cursor.fetchone()
    
    def get_local_image_tag(self, is_man,tag):
        """根据TAG查找图片
        id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify
        """
        test_conn()
        sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify FROM LocalSetu where man = ? AND (tag like ? OR pixiv_tag like ? OR pixiv_tag_t like ?) AND verify = 0 ORDER BY random() limit 1"
        cursor.execute(sql,(is_man,tag,tag,tag))
        conn.commit()
        return cursor.fetchone()
    
    def get_original_image(self, id):
        """查询原图是否存在
        pixiv_url,verify,pixiv_name,pixiv_id,url
        """
        test_conn()
        sql="SELECT pixiv_url,verify,pixiv_name,pixiv_id,url FROM LocalSetu where id = ?"
        cursor.execute(sql,(id,))
        conn.commit()
        return cursor.fetchone()
    
    def update_original_image(self,pixiv_id,pixiv_tag,pixiv_tag_t,r18,pixiv_img_url,pixiv_name,id):
        """更新原图信息"""
        test_conn()
        sql = "update LocalSetu set pixiv_id = ?,pixiv_tag = ?,pixiv_tag_t = ?,r18 = ?,pixiv_url = ?,pixiv_name = ? where id = ?"
        cursor.execute(sql,(pixiv_id,pixiv_tag,pixiv_tag_t,r18,pixiv_img_url,pixiv_name,id))
        conn.commit()
        
class loadImgDao:
    def __init__(self):
        test_conn()
        
    def load_image(self,url,user,tag,is_man,tencent_url):
        """上传消息类型的图片"""
        test_conn()
        sql="INSERT OR IGNORE INTO LocalSetu (id,url,user,date,tag,man,tencent_url) VALUES (NULL,?,?,datetime('now','localtime'),?,?,?)"
        cursor.execute(sql,(url,user,tag,is_man,tencent_url))
        id=cursor.lastrowid
        conn.commit()
        return id
    
    #好像文件类型没啥区别？先用消息的了
    def load_file(self,url,user,tag,is_man):
        """上传文件类型的图片"""
        sql="INSERT OR IGNORE INTO LocalSetu (id,url,user,date,tag,man) VALUES (NULL,?,?,datetime('now'),?,?)"
        cursor.execute(sql,(url,user,tag,is_man))
        id=cursor.lastrowid
        conn.commit()
        return
    
    def check_url(self,url):
        """检查url是否重复"""
        sql="SELECT id FROM LocalSetu where url = ?"
        cursor.execute(sql,(url,))
        conn.commit()
        return cursor.fetchone()
     
        
class verifyDao:
    def __init__(self):
        test_conn()
        
    def update_verify_stats(self,id:int, data:int):
        """
        更新审核状态
        id: 色图ID
        data: 0:通过, 1:待审核
        """
        try:
            test_conn()
            sql = f"update LocalSetu set verify = {data} where id = ?"
            cursor.execute(sql,(id,))
            conn.commit()
            return data
        except:
            return 1

    def update_verify_info(self,id:int, pixiv_id ,pixiv_tag ,pixiv_tag_t ,r18 ,pixiv_url ):
        """
        更新审核状态
        id: 色图ID
        pixiv_id: P站作品ID
        pixiv_tag：日文TAG
        pixiv_tag_t: 中文TAG
        r18： 是否R18
        pixiv_url： P站大图链接
        """
        try:
            test_conn()
            sql = "update LocalSetu set pixiv_id = ?,pixiv_tag = ?,pixiv_tag_t = ?,r18 = ?,pixiv_url = ? where id = ?"
            cursor.execute(sql,(pixiv_id,pixiv_tag,pixiv_tag_t,r18,pixiv_url,id))
            conn.commit()
            return 0
        except:
            return 1

class normalDao:
    def __init__(self):
        test_conn()
        
    def get_tecent_url(self,id):
        """检查腾讯url是否存在"""
        sql="SELECT url,tencent_url FROM LocalSetu where id = ?"
        cursor.execute(sql,(id,))
        return cursor.fetchone()