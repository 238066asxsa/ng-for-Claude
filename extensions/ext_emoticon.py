import random

from httpx import AsyncClient

from .Extension import Extension

# 扩展的配置信息，用于ai理解扩展的功能 *必填*
ext_config: dict = {
    "name": "emoticon",
    "arguments": {
        "keyword": "str",  # 关键字
    },
    "description": "Send a emoticon related to the keyword(in chinese). usage in response: /#emoticon&开心#/",
    # 参考词，用于上下文参考使用，为空则每次都会被参考(消耗token)
    "refer_word": [],
    # 每次消息回复中最大调用次数，不填则默认为99
    "max_call_times_per_msg": 3,
    # 作者信息
    "author": "KroMiose",
    # 版本
    "version": "0.0.1",
    # 扩展简介
    "intro": "发送表情包",
    # 可用会话类型 (server即MC服务器 | chat即QQ聊天)
    "available": ["chat"],
}


class CustomExtension(Extension):
    async def call(self, arg_dict: dict, _: dict) -> dict:
        """当扩展被调用时执行的函数 *由扩展自行实现*

        参数:
            arg_dict: dict, 由ai解析的参数字典 {参数名: 参数值}
        """
        custom_config: dict = self.get_custom_config()  # 获取yaml中的配置信息

        token = custom_config.get("token", None)
        if token is None:
            return {"text": "[ext_emoticon] 请在配置文件中填写alapi访问token"}

        keyword = arg_dict.get("keyword", "")
        req_args = {
            "token": custom_config["token"],
            "keyword": str(keyword),
            "page": 1,
            "type": 7,
        }

        url = "https://v2.alapi.cn/api/doutu"

        try:
            async with AsyncClient() as cli:
                res = (await cli.get(url, params=req_args, timeout=10)).json()
        except Exception as e:
            return {"text": f"[ext_emoticon] 访问api时发生错误: {e}"}

        if res.get("data") and len(res["data"]) > 0:
            # 从返回的data中随机选择一个返回
            return {"image": random.choice(res["data"])}

        return {
            "text": f"[ext_emoticon] 未找到与'{keyword}'相关的表情"
            if self.get_custom_config().get("debug", False)
            else None
        }

    def __init__(self, custom_config: dict):
        super().__init__(ext_config.copy(), custom_config)
