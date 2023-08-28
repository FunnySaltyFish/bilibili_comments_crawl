
from traceback import format_exc, print_exc
import asyncio
import httpx
import json
from typing import List, Dict, Any, TypeAlias
from async_pool import AsyncPool

JSON_TYPE: TypeAlias = Dict[str, Any]
COMMON_HEADERS = {
    "Origin": "https://www.bilibili.com",
    "Sec-Ch-Ua": '"Chromium";v="116", "Not)A;Brand";v="24", "Microsoft Edge";v="116"'
}

pool = AsyncPool(maxsize=16)

async def get_html(url: str, params: Dict = None, headers: Dict = None, timeout: int = 30):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=timeout, params=params, headers=headers)
            r.raise_for_status() # 如果状态不是200，引发HTTPError异常
            return r.text
    except Exception as e:
        print_exc()
        return "产生异常"
    
async def get_one_page(oid: int, page: int):
    """获取范围：一个回复页"""
    params = {
        "type": 1,
        "oid": oid,
        "sort": 2,
        "nohot": 0,
        "ps": 20,
        "pn": page
    }
    url = "https://api.bilibili.com/x/v2/reply/main"
    
    text = await get_html(url, params, COMMON_HEADERS)
    obj = json.loads(text)
    return obj

# https://api.bilibili.com/x/v2/reply/reply?csrf=9b261f0d10434bbefd17d7f4bd8247f2&oid=2&pn=1&ps=10&root=917945205&type=1
async def get_one_page_reply(oid: int, page: int, r_root: int):
    """获取一楼的一页评论"""
    params = {
        "type": 1,
        "oid": oid,
        "ps": 20,
        "pn": page,
        "root": r_root
    }
    url = "https://api.bilibili.com/x/v2/reply/reply"
    text = await get_html(url, params, COMMON_HEADERS)
    obj = json.loads(text)
    print("爬取 r_root: {}, page: {} 完毕".format(r_root, page))
    await asyncio.sleep(0.01)
    return obj["data"]["replies"]

async def get_reply(oid: int, r_root: int, total_count: int):
    """获取某个楼层的所有回复"""
    total_page = total_count // 20 + 1
    replies = []
    for page in range(1, total_page + 1):
        print("正在爬取 r_root: {}, page: {}".format(r_root, page))
        pool.submit(get_one_page_reply(oid, page, r_root), callback=lambda future: replies.extend(future.result()))
    pool.wait()
    return replies


def build_conv_from_replies(root_reply: JSON_TYPE, replies: List[JSON_TYPE]) -> List[List[Dict]]:
    conv = []
    replies_dict = {}
    replies.insert(0, root_reply)

    def backtrace(parent, conv):
        if parent == 0 or parent not in replies_dict:
            return
        conv.append(replies_dict[parent])
        backtrace(replies_dict[parent]['parent'], conv)


    # 将replies数据转换成字典形式
    for reply in replies:
        rpid = reply['rpid']
        parent = reply['parent']
        content = reply['content']['message']
        uname = reply['member']['uname']
        replies_dict[rpid] = {'parent': parent, 'content': content, 'uname': uname}

    for reply in replies_dict.values():
        if reply['parent'] == 0:
            conv.append([reply])
        else:
            conv.append([reply])
            backtrace(reply['parent'], conv[-1])

    conversations = []
    for c in conv:
        # 过滤：
        # 1. 评论数小于2的对话
        if len(c) <= 2:
            continue
        temp = []
        for item in reversed(c):
            content = item['content']
            if content.startswith('回复 @'):
                content = content.split(':')[1]
            temp.append({
                'from': item['uname'],
                'value': content
            })
        conversations.append(temp)
    
    return conversations



    
async def crawl_bilibili_comments(oid: int):
    """https://api.bilibili.com/x/v2/reply/main?csrf=9b261f0d10434bbefd17d7f4bd8247f2&mode=3&oid=275076584&pagination_str=%7B%22offset%22:%22%7B%5C%22type%5C%22:1,%5C%22direction%5C%22:1,%5C%22session_id%5C%22:%5C%221733821037173918%5C%22,%5C%22data%5C%22:%7B%7D%7D%22%7D&plat=1&type=1
    type	num	评论区类型代码	必要	类型代码见表
    oid	num	目标评论区 id	必要	
    sort	num	排序方式	非必要	默认为0
    0：按时间
    1：按点赞数
    2：按回复数
    nohot	num	是否不显示热评	非必要	默认为0
    1：不显示
    0：显示
    ps	num	每页项数	非必要	默认为20
    定义域：1-20
    pn	num	页码	非必要	默认为1
    """

    page = 1
    print("开始爬取评论")
    obj = await get_one_page(oid, page)
    # with open("bilibili_comments_full.json", "w", encoding="utf-8") as f:
    #     json.dump(obj, f, ensure_ascii=False, indent=4)

    video_replies = obj["data"]["replies"]
    total_page: int = obj["data"]["cursor"]["all_count"] // 20 + 1
    # 获取所有评论
    # 并发 8个协程

    all_comment_replies = {

    }

    def callback(future: asyncio.Future):
        pass

    
    # for page in range(1, total_page + 1):
    #     pool.submit(get_one_page(oid, page))


    comment_replies: Dict[str, Any] = await get_reply(oid, video_replies[0]["rpid"], video_replies[0]["rcount"])

    # print(obj)
    # with open("bilibili_comments_replies.json", "w", encoding="utf-8") as f:
    #     json.dump(comment_replies, f, ensure_ascii=False, indent=4)
    root_reply = video_replies[0]
    conversations = build_conv_from_replies(root_reply, comment_replies)
    with open("bilibili_comments_replies_convs.json", "w", encoding="utf-8") as f:
        json.dump(conversations, f, ensure_ascii=False, indent=4) 

async def main():
    await crawl_bilibili_comments(2)

if __name__ == "__main__":
    asyncio.run(main())

        


    



