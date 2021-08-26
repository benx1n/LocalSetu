# LocalSetu

基于HoshinoBot v2的本地setu插件（说不定之后会接入在线api呢）

## 改进

- [x] 全功能支持私聊
- [x] 支持所有用户上传图片，提交删除图片申请，共同维护色图库
- [x] 支持按上传者，ID，TAG等模糊查询色图
- [x] 支持并发上传时自定义每张TAG
- [x] 自动审核上传图片，未通过自动提交申请
- [x] 自动获取上传图片P站id，中日文tag，是否r18，原图文件
- [x] 自动检测重复色图（以P站id及md5作唯一性约束）
- [x] 优化指令，空参时自动进入上传、审核模式，方便手机端操作
- [x] 权限分离，普通用户无权进行敏感操作，全申请均可自动推送至审核人员
- [x] 支持反和谐
- [x] 多线程并发，大幅优化效率
- [x] 数据库基于mysql，方便进行数据处理，数据结构可高度自定义
- [x] 支持上传男同图，指令区分（不是

## 部署方法

1. 在HoshinoBot的插件目录modules下clone本项目 `git clone https://github.com/benx1n/LocalSetu.git`
2. 本地部署mysql
3. 获取[sauceNAO apikey](https://saucenao.com/)及[Pixiv refresh_token](https://gist.github.com/upbit/6edda27cb1644e94183291109b8a5fde)用于自动获取图片信息
4. 将配置文件 `config_default.json` 重命名为 `config.json` , 修改配置文件中的设置
5. 在 `config/__bot__.py`的模块列表里加入 `LocalSetu`
6. 重启hoshinoBot

## 指令说明

- kkqyxp/kkntxp[keyword]：随机发送色图/男同图，其中keyword为可选参数，支持ID、@上传者、TAG模糊查询
- 上传色/男图[TAG][图片][TAG][图片][TAG][图片]，其中TAG为可选参数，可跟多张图片
- 上传色/男图[无参数]：进入上传模式，该模式下用户发送的所有图片均视为上传，无操作20秒后自动退出
- 删除色图[ID]：删除指定ID色图，非审核人员仅可删除本人上传的色图，删除他人色图请使用'申请删除色图'
- 申请删除色图[ID]:提交色图删除申请，自动推送至审核人员
- 修改TAG[ID][TAG]：修改指定ID的自定义TAG
- 反和谐[ID]：色图被TX屏蔽时使用该指令，进行一次反和谐，后续发送色图均使用反和谐后文件

## 以下指令仅限审核人员使用

- 审核色图[上传][删除]：进入审核模式，每次发送待审核的色图，使用指令[保留][删除]后自动发送下一张，发送[退出审核]或20秒无操作自动退出
- 快速审核[ID]：快速通过指定ID的申请（默认保留）

## TODO

- 改用Sqlite

## 感谢

[HoshinoBot](https://github.com/Ice-Cirno/HoshinoBot)<br>
[go-cqhttp](https://github.com/Mrs4s/go-cqhttp)<br>
[PicImageSearch](https://github.com/kitUIN/PicImageSearch)<br>
[pixivpy](https://github.com/upbit/pixivpy)<br>

## 开源协议

GPL-3.0 License
