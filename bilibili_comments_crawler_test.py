import asyncio
import json
from traceback import print_exc
from typing import Any, Dict, List, Optional, TypeAlias

import httpx
from bilibili_api.credential import Credential

from async_pool import AsyncPool
# config 中包含了 BILI_JCT, SESSDATA, BUVID3, DEDE_USER_ID, AT_TIME_VALUE
from config import *

JSON_TYPE: TypeAlias = Dict[str, Any]

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
        "mode": 2,
        "pagination_str": '{"offset":"%s"}' % pagination_str.replace('"', r"\""),
    }
    # pagination_str: {"offset":"{\"type\":1,\"direction\":1,\"session_id\":\"1733963713068881\",\"data\":{}}"}
    url = "https://api.bilibili.com/x/v2/reply/main"
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

    print("爬取到的第 {} 页，第一条评论是 {}".format(
        page, video_replies[0]["content"]["message"]))
    return obj["data"]["cursor"]["pagination_reply"].get("next_offset")


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
            # next_page = await crawl_one_page_video(oid, page, pagination_str=pagination, client=client)
            next_page = await crawl_one_page_video(oid, page, pagination_str=pagination, client=client)

            print("-- 爬取视频 {} 的第 {} 页评论完毕，下一页: {}".format(oid, page, next_page))
            if next_page is None:
                print("- 视频 {} 的评论爬取完毕".format(oid))
                break
            await asyncio.sleep(0.1)
            pagination = next_page


async def refresh_cookie_if_necessary():
    need_refresh = await credential.check_refresh()
    if need_refresh:
        print("cookie 已过期，正在刷新")
        await credential.refresh()
        print("cookie 刷新成功")
    else:
        print("cookie 未过期，无需刷新")


async def main():
    await refresh_cookie_if_necessary()
    await crawl_one_video(2)

if __name__ == "__main__":
    asyncio.run(main())
