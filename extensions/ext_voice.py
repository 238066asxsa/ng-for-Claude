"""
启用tecent翻译 可以在YAML 中填入下面的参数
ng_voice_translate_on : True
tencentcloud_common_region : "ap-shanghai"
tencentcloud_common_secretid : "xxxxx"
tencentcloud_common_secretkey : "xxxxx"
ng_voice_tar : 'ja'
"""

import asyncio
import base64
import os
import urllib
import uuid
from binascii import b2a_base64
from hashlib import sha1
from hmac import new
from random import randint
from sys import maxsize, version_info
from time import time

import anyio
from aiohttp import request
from loguru import logger
from nonebot import get_driver
from nonebot.exception import ActionFailed

from .Extension import Extension

try:
    from ujson import loads as loadJsonS
except:
    from json import loads as loadJsonS

# 扩展的配置信息，用于ai理解扩展的功能 *必填*
ext_config: dict = {
    "name": "voice",  # 扩展名称，用于标识扩展
    "arguments": {
        "sentence": "str",  # 需要转换的文本
    },
    # 扩展的描述信息，用于提示ai理解扩展的功能 *必填* 尽量简短 使用英文更节省token
    "description": "Send a voice sentence. (usage in response: /#voice&你好#/)",
    # 参考词，用于上下文参考使用，为空则每次都会被参考(消耗token)
    "refer_word": [],
    # 作者信息
    "author": "KroMiose",
    # 版本
    "version": "0.0.2",
    # 扩展简介
    "intro": "发送语音消息(支持翻译)",
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

        ng_voice_translate_on = custom_config.get(
            "ng_voice_translate_on", False
        )  # 是否启用翻译
        tencentcloud_common_region = custom_config.get(
            "tencentcloud_common_region", "ap-shanghai"
        )  # 腾讯翻译-地区
        tencentcloud_common_secretid = custom_config.get(
            "tencentcloud_common_secretid", "xxxxx"
        )  # 腾讯翻译-密钥id
        tencentcloud_common_secretkey = custom_config.get(
            "tencentcloud_common_secretkey", "xxxxx"
        )  # 腾讯翻译-密钥
        ng_voice_tar = custom_config.get("g_voice_tar", "ja")  # 翻译目标语言
        is_base64 = custom_config.get("is_base64", False)  # 是否使用base64编码

        voice_path = "voice_cache/"
        # 创建缓存文件夹
        if not os.path.exists(voice_path):
            os.mkdir(voice_path)

        # 获取参数
        raw_text = arg_dict.get("sentence", None)

        # 从这里开始翻译

        # 腾讯翻译-签名
        # config = get_driver().config

        async def getReqSign(params: dict) -> str:
            common = {
                "Action": "TextTranslate",
                "Region": f"{tencentcloud_common_region}",
                "Timestamp": int(time()),
                "Nonce": randint(1, maxsize),
                "SecretId": f"{tencentcloud_common_secretid}",
                "Version": "2018-03-21",
            }
            params.update(common)
            sign_str = "POSTtmt.tencentcloudapi.com/?"
            sign_str += "&".join("%s=%s" % (k, params[k]) for k in sorted(params))
            secret_key = tencentcloud_common_secretkey
            if version_info[0] > 2:
                sign_str = bytes(sign_str, "utf-8")
                secret_key = bytes(
                    secret_key, "utf-8"
                )  # TODO else 是否应该直接 return? 下一行的new 函数并不接受 str 类型的参数
            hashed = new(secret_key, sign_str, sha1)
            signature = b2a_base64(hashed.digest())[:-1]
            if version_info[0] > 2:
                signature = signature.decode()
            return signature

        async def q_translate(message) -> str:
            _source_text = message
            _source = "auto"
            _target = ng_voice_tar
            try:
                endpoint = "https://tmt.tencentcloudapi.com"
                params = {
                    "Source": _source,
                    "SourceText": _source_text,
                    "Target": _target,
                    "ProjectId": 0,
                }
                params["Signature"] = await getReqSign(params)
                # 加上超时参数
                async with request("POST", endpoint, data=params) as resp:
                    data = loadJsonS(await asyncio.wait_for(resp.read(), timeout=30))[
                        "Response"
                    ]
                    message = data["TargetText"]
            except ActionFailed as e:
                logger.warning(
                    f"ActionFailed {e.info['retcode']} {e.info['msg'].lower()} {e.info['wording']}"
                )
            except TimeoutError as e:
                logger.warning(f"TimeoutError {e}")
            return message

        # 到这里翻译函数结束

        if ng_voice_translate_on is True:
            t_result = await q_translate(raw_text)
        else:
            t_result = raw_text
        text = t_result + "~"  # 加上一个字符，避免合成语音丢失结尾
        text = urllib.parse.quote(text)  # url编码

        # ! moegoe.azurewebsites.net 是一个公开的语音合成api，非本人搭建，请勿滥用 (tip by KroMiose)
        # 该api只支持日语，如果传入其它语言，会导致合成结果不可预知
        # 如果你开启了翻译就没事了
        url = f"https://moegoe.azurewebsites.net/api/speak?text={text}&id=0"

        # todo: 如果需要使用本地的语音合成api，请取消注释下面的代码，并自行改为您的api地址，将填入合成文本的地方改为{text}
        # url = f"http://127.0.0.1:23211/to_voice?text={text}"

        # 下载语音文件
        async with request("GET", url) as r:
            file_name = f"{voice_path}{uuid.uuid1()}.ogg"
            content = await r.read()
            audio_data = base64.b64decode(content) if is_base64 else content

        file_path = await (anyio.Path(file_name)).resolve()
        await file_path.write_bytes(audio_data)
        local_url = file_path.as_uri()

        if text is not None:
            return {
                "voice": local_url,  # 语音url
                "text": f"[语音消息] {raw_text}",  # 文本
            }
        return {}

    def __init__(self, custom_config: dict):
        super().__init__(ext_config.copy(), custom_config)
