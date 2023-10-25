import time

from httpx import AsyncClient
from nonebot import logger

from .Extension import Extension

# 扩展的配置信息，用于ai理解扩展的功能 *必填*
ext_config: dict = {
    "name": "search",  # 扩展名称，用于标识扩展
    "arguments": {
        "keyword": "str",  # 关键字
    },
    # 扩展的描述信息，用于提示ai理解扩展的功能 *必填* 尽量简短 使用英文更节省token
    # 如果bot无法理解扩展的功能，可适当添加使用示例 格式: /#扩展名&参数1&...&参数n#/
    "description": "Search for keywords on the Internet and wait for the results. Use when you need to get real-time information or uncertain answers. (usage in response: /#search&keyword#/))",
    # 参考词，用于上下文参考使用，为空则每次都会被参考(消耗token)
    "refer_word": [],
    # 每次消息回复中最大调用次数，不填则默认为99
    "max_call_times_per_msg": 1,
    # 作者信息
    "author": "CCYellowStar",
    # 版本
    "version": "0.0.4",
    # 扩展简介
    "intro": "让机器人openai能上网搜索",
    # 调用时是否打断响应 启用后将会在调用后截断后续响应内容
    "interrupt": True,
}


class CustomExtension(Extension):
    async def call(self, arg_dict: dict, _: dict) -> dict:
        """当扩展被调用时执行的函数 *由扩展自行实现*

        参数:
            arg_dict: dict, 由ai解析的参数字典 {参数名: 参数值}
        """
        custom_config: dict = self.get_custom_config()  # 获取yaml中的配置信息
        proxy = custom_config.get("proxy")
        max_results = custom_config.get("max_results", 3)

        if proxy and (not proxy.startswith("http")):
            proxy = "http://" + proxy

        # 从arg_dict中获取参数
        keyword = arg_dict.get("keyword", None)

        if (
            keyword is None
            or keyword == self._last_keyword
            or time.time() - self._last_call_time < 10
        ):
            return {}

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.63"
        }
        url = "https://ddg-webapp-search.vercel.app/search"
        async with AsyncClient(proxies=proxy) as cli:
            data = (
                await cli.get(
                    url,
                    headers=headers,
                    params={
                        "q": keyword,
                        "max_results": max_results,
                        "region": "cn-zh",
                    },
                )
            ).json()
        logger.debug(data)

        try:
            text = "\n".join(
                [f"{data[i]['body']}" for i in range(len(data)) if i < max_results]
            )
            text = text.replace("\n\n", "  ")
            # text = data[0]['body']+"\n"+data[0]['href']+"\n"+data[1]['body']+"\n"+data[1]['href']+"\n"+data[2]['body']+"\n"+data[2]['href']
            # refer_url = data[0]['href']+"\n"+data[1]['href']+"\n"+data[2]['href']
        except:
            return {
                "text": f"[ext_search] 未找到关于'{keyword}'的信息",
                "image": None,  # 图片url
                "voice": None,  # 语音url
            }

        # 返回的信息将会被发送到会话中
        self._last_keyword = keyword
        self._last_call_time = time.time()
        return {
            "text": f"[ext_search] 搜索: {keyword} [完成]",
            "notify": {
                "sender": f"[Search results for {keyword} (Please refer to the following information to respond)]",
                "msg": f"{text}",
            },
            "wake_up": True,  # 是否再次响应
        }

    def __init__(self, custom_config: dict):
        super().__init__(ext_config.copy(), custom_config)
        self._last_keyword = None
        self._last_call_time = 0
