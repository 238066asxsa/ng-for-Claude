from .Extension import Extension
from httpx import AsyncClient

# 扩展的配置信息，用于ai理解扩展的功能 *必填*
ext_config: dict = {
    "name": "AnimePic",  # 扩展名称，用于标识扩展
    "arguments": {},
    "description": "send 1 random anime picture. (not parameters! usage in response: /#AnimePic#/)",
    # 参考词，用于上下文参考使用，为空则每次都会被参考(消耗token)
    "refer_word": ["图", "pic", "Pic", "再", "还", "涩", "色"],
    # 每次消息回复中最大调用次数，不填则默认为99
    "max_call_times_per_msg": 3,
    # 作者信息
    "author": "KroMiose",
    # 版本
    "version": "0.0.1",
    # 扩展简介
    "intro": "发送随机二次元图片",
    # 可用会话类型 (server即MC服务器 | chat即QQ聊天)
    "available": ["chat"],
}


class CustomExtension(Extension):
    async def call(self, _: dict, __: dict) -> dict:
        """当扩展被调用时执行的函数 *由扩展自行实现*

        参数:
            arg_dict: dict, 由ai解析的参数字典 {参数名: 参数值(类型为str)}
        """
        # custom_config: dict = self.get_custom_config()  # 获取yaml中的配置信息

        url = "https://api.ixiaowai.cn/api/api.php"
        async with AsyncClient(verify=False, timeout=10) as cli:
            img_src = (
                (await cli.get(url, params={"return": "json"})).json().get("imgurl")
            )

        if not img_src:
            return {
                "text": "[来自扩展] 发送图片错误或超时...",
                "image": None,  # 图片url
                "voice": None,  # 语音url
            }

        # 返回的信息将会被发送到会话中
        return {
            "text": None,  # 文本信息
            "image": img_src,  # 图片url
            "voice": None,  # 语音url
        }

    def __init__(self, custom_config: dict):
        super().__init__(ext_config.copy(), custom_config)
