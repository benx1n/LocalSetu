import os
from .dao import normalDao
from .utils import setu_folder,download

async def redownload_from_tencent(id):
    result = normalDao().get_tecent_url(id)
    if not result:
        return f'id{id}不存在~~~'
    if not result[1]:
        return f'id{id}的腾讯服务器url不存在~~~'
    local_url = os.path.join(setu_folder,result[0])
    if not os.path.exists(os.path.abspath(local_url)):
        try:
            await download(result[1], local_url)
            msg = f'id{id}下载成功'
        except:
            msg = f'id{id}下载失败，可能是腾讯服务器url过期了~'
    else:
        msg = f'id{id}本地文件已存在哦~'
    return msg