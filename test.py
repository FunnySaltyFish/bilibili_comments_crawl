import httpx

# pagination_str = '{"next_offset":"{\"type\":1,\"direction\":1,\"session_id\":\"1734022216194643\",\"data\":{}}"}'
credential = {'SESSDATA': '6f8968ca%2C1708925662%2C03189%2A82uIXznvvX-zedaQ3WyRIOqn6Dh7VUnTNvXKRykeFXvVUHLB0FvrgOi_Cf3ffrgVldMCvuYgAAPgA', 'buvid3': 'E4483DB9-FBB8-2739-688D-E0318C45C90B57149infoc', 'bili_jct': '1814dc09cd43ee4d10f37c9bcc364f22', 'DedeUserID': '452976562', 'ac_time_value': 'c8aaa7952b33fadf5f5559a5a3104f82'}
def make_request():
    url = 'https://api.bilibili.com/x/v2/reply/main?type=1&oid=275261884&mode=3&pagination_str=%7B%22type%22%3A1%2C%22direction%22%3A1%2C%22data%22%3A%7B%22pn%22%3A2%7D%7D'
    #'https://api.bilibili.com/x/v2/reply/wbi/main?oid=532782563&type=1&mode=3&pagination_str=%7B%22offset%22:%22%7B%5C%22type%5C%22:1,%5C%22direction%5C%22:1,%5C%22session_id%5C%22:%5C%221734022946219014%5C%22,%5C%22data%5C%22:%7B%7D%7D%22%7D&plat=1&web_location=1315875&w_rid=086e78f123110885e817f6f895c4e389&wts=1693381842'
    #'https://api.bilibili.com/x/v2/reply/main?type=1&oid=275261884&mode=3&pagination_str=%7B%22type%22%3A1%2C%22direction%22%3A1%2C%22session_id%22%3A%221734021566377916%22%2C%22data%22%3A%7B%7D%7D'
    headers = {
        # 'authority': 'api.bilibili.com',
        # 'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        # 'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,en-GB;q=0.6',
        # 'cache-control': 'no-cache',
        'cookie': "; ".join([f"{k}={v}" for k, v in credential.items()]),
        # 'cookie': 'buvid3=E4483DB9-FBB8-2739-688D-E0318C45C90B57149infoc; buvid4=7DC5DC9D-34FD-E06D-263D-F362980017FC80313-022012419-aLF1sSKi5yFqdKrp9fhC4A%3D%3D; SESSDATA=6f8968ca%2C1708925662%2C03189%2A82uIXznvvX-zedaQ3WyRIOqn6Dh7VUnTNvXKRykeFXvVUHLB0FvrgOi_Cf3ffrgVldMCvuYgAAPgA; bili_jct=1814dc09cd43ee4d10f37c9bcc364f22;',
        # 'pragma': 'no-cache',
        # 'sec-ch-ua': '"Chromium";v="116", "Not)A;Brand";v="24", "Microsoft Edge";v="116"',
        # 'sec-ch-ua-mobile': '?0',
        # 'sec-ch-ua-platform': '"Windows"',
        # 'sec-fetch-dest': 'document',
        # 'sec-fetch-mode': 'navigate',
        # 'sec-fetch-site': 'none',
        # 'sec-fetch-user': '?1',
        # 'upgrade-insecure-requests': '1',
        # 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.62'
    }
    
    response = httpx.get(url, headers=headers)
    return response


# 调用函数进行请求
response = make_request()

# 打印响应内容
print("那迪叶" in response.text)
with open('test_another_video.json', 'w', encoding='utf-8') as f:
    f.write(response.text)

# Cookie 是关键参数
#