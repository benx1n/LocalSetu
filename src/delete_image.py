import os
import traceback
from .dao import deleteDao
from .utils import config,setu_folder
from hoshino.typing import MessageSegment

verify_group = config['verify_group']

async def delete_image(id,user,bot,ev):
    try:
        results = deleteDao().get_info(id)
        if not results:
            return '请检查id是否正确~'
        else:
            for row in results:
                url = row[0]
                if int(user) not in verify_group:
                    if user != row[1]:
                        deleteDao().apply_for_delete(id)
                        for ves in verify_group:
                            await bot.send_private_msg(self_id=ev.self_id, user_id=int(ves),message=f'有新的删除申请,id:{id}'+str(MessageSegment.image(f'file:///{os.path.abspath(os.path.join(setu_folder,url))}')))
                        return "这张涩图不是您上传的哦~已加入待删除列表，请等待维护组审核"
                    else:
                        deleteDao().delete_image(id)
                        os.remove(os.path.join(setu_folder, url))
                        return f"OvO~涩图{id}删掉了~"
                else:
                    deleteDao().delete_image(id)
                    os.remove(os.path.join(setu_folder, url))
                    return f"OvO~涩图{id}删掉了~"
    except:
        traceback.print_exc()
        return f"QAQ~删涩图{id}的时候出现了问题，但一定不是我的问题~"        