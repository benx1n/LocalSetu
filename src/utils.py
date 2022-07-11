import httpx
from pathlib import Path
import hjson
import random
import hashlib

dir_path = Path(__file__).parent
config_path = dir_path.parent / 'config.hjson'
config = hjson.load(open(config_path, 'r', encoding='utf8'))

async def download(url, path, proxy = {}):
    async with httpx.AsyncClient(proxies=proxy) as client:
        resp = await client.get(url, timeout=None)
        content = await resp.read()
        with open(path, 'wb') as f:
            f.write(content)


#下面的函数随机更改图片的某个像素值，用于反和谐
async def image_random_one_pixel(img1):  
    w,h=img1.size
    pots=[(0,0),(0,h-1),(w-1,0),(w-1,h-1)]
    pot=pots[random.randint(0,3)]
    img1.putpixel(pot,(random.randint(0,255),random.randint(0,255),random.randint(0,255)))
    return img1

#图片文件转为MD5
async def image2MD5(filename):
    file = open(filename, "rb")
    md = hashlib.md5()
    md.update(file.read())
    res1 = md.hexdigest()
    return res1+".image"