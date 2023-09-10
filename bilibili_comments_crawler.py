
from traceback import format_exc, print_exc
import asyncio
import httpx
import json
from typing import List, Dict, Any, TypeAlias, Optional
from async_pool import AsyncPool
import os
from urllib.parse import urlencode
from bilibili_api.credential import Credential
from config import *

JSON_TYPE: TypeAlias = Dict[str, Any]

#
COMMON_HEADERS = {
    "Origin": "https://www.bilibili.com",
    "Authority": "api.bilibili.com",
    "Sec-Ch-Ua": '"Chromium";v="116", "Not)A;Brand";v="24", "Microsoft Edge";v="116"',
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
}

# https://nemo2011.github.io/bilibili-api/#/get-credential
if not (SESSDATA and BILI_JCT and BUVID3 and DEDE_USER_ID and AT_TIME_VALUE):
    raise ValueError(
        "请在 .env 中填写 SESSDATA, BILI_JCT, BUVID3, DEDE_USER_ID, AT_TIME_VALUE")

credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT,
                        buvid3=BUVID3, dedeuserid=DEDE_USER_ID, ac_time_value=AT_TIME_VALUE)
print("credential: ", credential.get_cookies())
pool = AsyncPool(maxsize=16)


def save_obj(obj: JSON_TYPE, filename: str):
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


async def get_html(url: str, params: Dict = None, headers: Dict = None, cookies: Dict = None, timeout: int = 30, client: httpx.AsyncClient = None):
    m_client = client
    try:
        if client is None:
            m_client = httpx.AsyncClient()
        # print("当前发送请求的 client ID: ", id(m_client))
        r = await m_client.get(url, timeout=timeout, params=params, headers=headers, cookies=cookies)
        r.raise_for_status()  # 如果状态不是200，引发HTTPError异常
        return r.text
    except Exception as e:
        print_exc()
        return "产生异常"
    finally:
        if client is None and m_client is not None:
            await m_client.aclose()


async def get_one_page(oid: int, pagination_str: str, client: httpx.AsyncClient = None):
    """获取范围：一个回复页"""
    params = {
        "type": 1,
        "oid": oid,
        "mode": 3,
        "pagination_str": '{"offset":"%s"}' % pagination_str.replace('"', r"\""),
    }
    # pagination_str: {"offset":"{\"type\":1,\"direction\":1,\"session_id\":\"1733963713068881\",\"data\":{}}"}
    url = "https://api.bilibili.com/x/v2/reply/main"
    # enc_wbi(params, await get_mixin_key())
    # print("-- url: ", url + "?" + urlencode(params))
    text = await get_html(url, params, COMMON_HEADERS, cookies=credential.get_cookies(), client=client)
    obj = json.loads(text)
    return obj


async def crawl_one_page_video(oid: int, page: int, pagination_str: str, client: httpx.AsyncClient) -> Optional[str]:
    """
    爬取一个视频一页的评论，返回下一页的 pagination_str
    """

    print("-- 开始爬取视频 {} 的第 {} 页评论".format(oid, page))
    obj = await get_one_page(oid, pagination_str, client)

    if obj["code"] != 0:
        print("爬取视频 {} 的第 {} 页评论失败，原因是 {} (code={})".format(
            oid, page, obj["message"], obj["code"]))
        return None
    video_replies = obj["data"]["replies"]

    for root_reply in video_replies:
        comment_replies: Dict[str, Any] = await get_reply(oid, root_reply["rpid"], root_reply["rcount"])
        conversations = build_conv_from_replies(root_reply, comment_replies)
        if conversations:
            save_obj(
                conversations, f"data/video_{oid}/page_{page}/rpid_{root_reply['rpid']}_convs.json")
            print("--- 保存 rpid 为 {:12d} 的评论并构建对话完毕，共 {:6d} 条".format(
                root_reply["rpid"], len(conversations)))
        else:
            print(
                "--- rpid 为 {:12d} 的评论没有符合要求的对话，跳过保存".format(root_reply["rpid"]))
        await asyncio.sleep(0.1)

    print("爬取到的第 {} 页，第一条评论是 {}".format(
        page, video_replies[0]["content"]["message"]))
    return obj["data"]["cursor"]["pagination_reply"].get("next_offset")


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
    return obj["data"].get("replies") or []


async def get_reply(oid: int, r_root: int, total_count: int):
    """获取某个楼层的所有回复"""
    total_page = total_count // 20 + 1
    replies = []
    for page in range(1, total_page + 1):
        if page % 10 == 0:
            print("---- 正在爬取 r_root: {}, page: {}".format(r_root, page))
        pool.submit(get_one_page_reply(oid, page, r_root),
                    callback=lambda future: replies.extend(future.result()))
    pool.wait()
    return replies


async def crawl_one_video(oid: int):
    """
    爬取一个视频的所有评论
    """
    print("- 开始爬取视频 {} 的评论".format(oid))
    url = "https://api.bilibili.com/x/v2/reply/count"
    params = {
        "type": 1,
        "oid": oid
    }
    text = await get_html(url, params, COMMON_HEADERS)
    obj = json.loads(text)
    total_page: int = obj["data"]["count"] // 20 + 1
    print("- 视频 {} 一共有 {} 页评论".format(oid, total_page))
    pagination = ''
    async with httpx.AsyncClient() as client:
        for page in range(1, total_page + 1):
            next_page = await crawl_one_page_video(oid, page, pagination_str=pagination, client=client)

            print("-- 爬取视频 {} 的第 {} 页评论完毕，下一页: {}".format(oid, page, next_page))
            if next_page is None:
                print("- 视频 {} 的评论爬取完毕".format(oid))
                break
            await asyncio.sleep(0.1)
            pagination = next_page


def build_conv_from_replies(root_reply: JSON_TYPE, replies: List[JSON_TYPE]) -> List[List[Dict]]:
    if not replies:
        return []

    conv = []
    replies_dict = {}
    replies.insert(0, root_reply)

    # 将replies数据转换成字典形式
    for reply in replies:
        rpid = reply['rpid']
        parent = reply['parent']
        content = reply['content']['message']
        uname = reply['member']['uname']
        replies_dict[rpid] = {'parent': parent,
                              'content': content, 'uname': uname}

    conv_tree = {}

    # 构建对话树
    for reply_id, reply in replies_dict.items():
        parent_id = reply['parent']
        if parent_id in conv_tree:
            conv_tree[parent_id].append(reply_id)
        else:
            conv_tree[parent_id] = [reply_id]

    # print(conv_tree)
    longest_paths = []
    path = []

    # DFS遍历所有根节点到叶子节点的路径
    def dfs(node):
        nonlocal path
        path.append(node)
        if node not in conv_tree:
            # 当前节点是叶子节点，保存路径
            longest_paths.append(path.copy())
        else:
            for child in conv_tree[node]:
                dfs(child)
        path.pop()

    # 从每个根节点开始进行DFS搜索
    for root in conv_tree[0]:
        dfs(root)

    # 根据路径获取对话链
    longest_conversations = []
    for path in longest_paths:
        conversation = []
        for node in path:
            conversation.append(replies_dict[node])
        longest_conversations.append(conversation)

    conv = longest_conversations

    conversations = []
    for c in conv:
        # 过滤：
        # 1. 评论数小于5的对话
        if len(c) < 5:
            continue
        temp = []
        for item in c:
            content = item['content']
            if content.startswith('回复 @'):
                content = content.split(':')[1]
            temp.append({
                'from': item['uname'],
                'value': content
            })
        conversations.append(temp)

    return conversations


async def refresh_cookie_if_necessary():
    need_refresh = await credential.check_refresh()
    if need_refresh:
        print("cookie 已过期，正在刷新")
        await credential.refresh()
        print("cookie 刷新成功")
        # cookie = credential.get_cookies()
        # COMMON_HEADERS["Cookie"] = "; ".join([f"{k}={v}" for k, v in cookie.items()])
    else:
        print("cookie 未过期，无需刷新")


async def main():
    await refresh_cookie_if_necessary()
    # oid 即为视频的 av 号，可以在某个视频的源码中找到
    await crawl_one_video(960513817)


if __name__ == "__main__":
    asyncio.run(main())
