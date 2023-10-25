from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr
from typing import Optional

from aiosmtplib import SMTP
from nonebot import logger

from .Extension import Extension

# 扩展的配置信息，用于ai理解扩展的功能 *必填*
ext_config: dict = {
    "name": "email",  # 扩展名称，用于标识扩展
    "arguments": {
        "receiver": "str",  # 目标邮箱地址
        "title": "str",  # 邮件标题
        "content": "str",  # 邮件内容
    },
    "description": "Send an email to the specified mailbox. (usage in response: /#email&receiver@mail.com&title&hello#/ , accessories are not supported)",
    # 参考词，用于上下文参考使用，为空则每次都会被参考(消耗token)
    "refer_word": [],
    # 每次消息回复中最大调用次数，不填则默认为99
    "max_call_times_per_msg": 5,
    # 作者信息
    "author": "KroMiose",
    # 版本
    "version": "0.0.1",
    # 扩展简介
    "intro": "向指定邮箱发送邮件",
}


class CustomExtension(Extension):
    async def call(self, arg_dict: dict, ctx_data: dict) -> dict:
        """当扩展被调用时执行的函数 *由扩展自行实现*

        参数:
            arg_dict: dict, 由ai解析的参数字典 {参数名: 参数值(类型为str)}
        """
        custom_config: dict = self.get_custom_config()  # 获取yaml中的配置信息

        # 从arg_dict中获取参数
        receiver = arg_dict.get("receiver", None)
        title = arg_dict.get("title", None)
        content = arg_dict.get("content", None)

        # 从custom_config中获取配置信息
        SMTP_ADDR = custom_config.get("SMTP_ADDR", "smtp.163.com")
        SMTP_PORT = custom_config.get("SMTP_PORT", None)
        SMTP_USE_TLS = custom_config.get("SMTP_USE_TLS", True)
        SMTP_CODE = custom_config.get("SMTP_CODE", None)  # 邮箱SMTP授权码
        SENDER_ADDR = custom_config.get("SENDER_ADDR", None)  # 发件人邮箱地址
        SENDER_NAME = ctx_data.get("bot_name", "MioseBot")  # 发件人名称

        if not (SMTP_CODE and SENDER_ADDR and SENDER_NAME):
            return {
                "text": "[ext_mail] 请先配置邮箱信息",
            }

        if not (receiver and content):
            return {
                "text": "[ext_mail] 缺少有效信息",
            }

        miose_bot_opt = MioseBotOpt(
            SMTP_ADDR, SMTP_PORT, SMTP_USE_TLS, SENDER_ADDR, SENDER_NAME, SMTP_CODE
        )
        ok, e = await miose_bot_opt.send_mail(receiver, title, content)
        if ok:
            return {"text": f"[ext_mail] 发送邮件({title})\n到{receiver}[成功]"}

        logger.opt(exception=e).exception("邮件发送失败")
        return {
            "text": "[ext_mail] 邮件发送失败",
        }

    def __init__(self, custom_config: dict):
        super().__init__(ext_config.copy(), custom_config)


class MioseBotOpt:
    def __init__(
        self,
        host_server: str,
        port: Optional[int],
        use_tls: bool,
        sender_addr: str,
        sender_name: str,
        ep_code: str,
    ):
        self.host_server = host_server
        self.port = port
        self.use_tls = use_tls
        self.sender = sender_addr
        self.send_name = sender_name
        self.ep_code = ep_code

    async def send_mail(self, recv_mail, title, context):
        """发送邮件

        Keyword arguments:
        recv_mail -- 接收者邮件地址
        title   -- 邮件标题
        context -- 邮件正文
        Return: 是否成功
        """

        from_mail, send_name = self.sender, self.send_name
        mail_title, mail_content = title, context

        # 发送邮件
        smtp = SMTP(self.host_server, port=self.port, use_tls=True)
        try:
            await smtp.connect()
            await smtp.login(self.sender, self.ep_code)
            msg = MIMEText(mail_content, "html", "utf-8")
            msg["Subject"] = Header(mail_title, "utf-8")
            msg["From"] = MioseBotOpt._format_addr("%s <%s>" % (send_name, from_mail))
            msg["To"] = MioseBotOpt._format_addr("%s <%s>" % (recv_mail, recv_mail))
            await smtp.sendmail(from_mail, recv_mail, msg.as_string())
            await smtp.quit()

        except Exception as e:
            smtp.close()
            return False, e

        return True, None

    @staticmethod
    def _format_addr(s):
        return formataddr(parseaddr(s))
