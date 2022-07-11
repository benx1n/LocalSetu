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
        """id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify"""
        sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify FROM LocalSetu where man = ? AND verify = 0 ORDER BY random() limit 1"
        cursor.execute(sql,(is_man,))
        conn.commit()
        return cursor.fetchone()
    
    def get_local_image_user(self, is_man,user):  
        """id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify"""
        sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify from LocalSetu where man = ? AND user = ? AND verify = 0 ORDER BY random() limit 1"
        cursor.execute(sql,(is_man,str(user)))
        conn.commit()
        return cursor.fetchone()
    
    def get_local_image_ID(self, is_man,id):
        """id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify"""
        test_conn()
        sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify FROM LocalSetu where man = ? AND id = ? ORDER BY random() limit 1"
        cursor.execute(sql,(is_man,id))
        conn.commit()
        return cursor.fetchone()
    
    def get_local_image_tag(self, is_man,tag):
        """id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify"""
        test_conn()
        sql="SELECT id,url,anti_url,user,date,tag,pixiv_tag_t,pixiv_id,pixiv_url,verify FROM LocalSetu where man = ? AND (tag like ? OR pixiv_tag like ? OR pixiv_tag_t like ?) AND verify = 0 ORDER BY random() limit 1"
        cursor.execute(sql,(is_man,tag,tag,tag))
        conn.commit()
        return cursor.fetchone()
    
    def get_original_image(self, id):
        """pixiv_url,verify,pixiv_name,pixiv_id,url"""
        test_conn()
        sql="SELECT pixiv_url,verify,pixiv_name,pixiv_id,url FROM LocalSetu where id = ?"
        cursor.execute(sql,(id,))
        conn.commit()
        return cursor.fetchone()
    
    def update_original_image(self,pixiv_id,pixiv_tag,pixiv_tag_t,r18,pixiv_img_url,pixiv_name,id):
        test_conn()
        sql = "update LocalSetu set pixiv_id = ?,pixiv_tag = ?,pixiv_tag_t = ?,r18 = ?,pixiv_url = ?,pixiv_name = ? where id = ?"
        cursor.execute(sql,(pixiv_id,pixiv_tag,pixiv_tag_t,r18,pixiv_img_url,pixiv_name,id))
        conn.commit()
        
        
        
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