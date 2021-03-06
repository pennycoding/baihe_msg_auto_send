# -*- coding:utf-8 -*-
import os
import re
import sys
import json
import math
import time
import random
import logging

from PIL import Image
from StringIO import StringIO
from urllib import quote, urlencode
from cookielib import LWPCookieJar, Cookie
from urllib2 import Request, build_opener, HTTPCookieProcessor

try:
    from msvcrt import getch
except ImportError:
    def getch():
        import tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class SendMessageError(Exception):
    pass


class MsgAutoSender(object):

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        "Accept-Language": "en-US,en;q=0.5",
        #"Cookie": "; ".join(map(lambda x: "=".join(x), data.items()))
    }

    messages = ["你好[微笑]"]

    data = {
        'txtLoginEMail': "",
        'txtLoginPwd': "",
        'chkRememberMe': "",
        'codeId': "",
        'codeValue': '',
        'event':'3',
        'spmp':'4.20.53.225.685',
        '_': "%d"%(time.time()*1000)
    }
    # 预登陆url
    url1 = 'http://my.baihe.com/Getinterlogin/gotoLogin?jsonCallBack=jQuery18308807729283968166_%d&'%(time.time()*1000)
    # 登陆成功后跳转到主页
    url2 = "http://u.baihe.com/?userid=&time=%d"%(time.time()*1000)
    # 用来获取一些默认的搜索条件（百合会根据你个人信息筛选出一些基本符合你要求的人群）
    url3 = "http://search.baihe.com/mystruts/nextSolrSearch.action?jsoncallback=jQuery183042376943520885857_1479472584212&callType=next&pageId=%%s&ord=1&_=%d"%(time.time()*1000)
    # 用来搜索默认条件下的妹纸
    url4 = "http://search.baihe.com/solrAdvanceSearch.action"
    # 向妹纸发送消息
    url5 = "http://msg.baihe.com/owner/api/sendMessage?jsonCallBack=jQuery18304671662130587029_1479300393335&toUserID=%%s&content=%%s&type=1&pathID=01.00.10402&_=%d&"%(time.time()*1000)
    # 登陆过频繁的话，会要求输验证，此url用来获取验证码图片
    url6 = "http://my.baihe.com/Getinterlogin/getVerifyPic?jsonCallBack=?&tmpId=%s"
    # 用来检查登陆次数，来判定是否需要输验证码了
    url7 = "http://my.baihe.com/Getinterlogin/getAccountTimes?jsonCallBack=jQuery183013238800936369732_1479556200186&userAccount=18353130797&_=1479556585384"
    # 用来验证验证码是否正确
    url8 = "http://my.baihe.com/Getinterlogin/checkVerifyPic?jsonCallBack=jQuery183010981413646438898_1480223919788&tmpId=%%s&checkcode=%%s&_=%d"%(time.time()*1000)
    # access_token生成
    acc_token = Cookie(version=0,
                                 name="accessToken",
                                 value='BH%d%d'%(time.time()*1000,math.floor(random.random()*1000000)),
                                 domain=".baihe.com",
                                 path="/",
                                 port=None,
                                 port_specified=False,
                                 domain_specified=True,
                                 domain_initial_dot=False,
                                 path_specified=True,
                                 secure=False,
                                 expires=None,
                                 discard=False,
                                 comment=None,
                                 comment_url=None,
                                 rest={},
                                 rfc2109=False)

    logger = logging.getLogger("send_msg")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler(sys.stdout))

    try:
        have_send_list = set(open("have_send_list.txt").read().strip(",").split(","))
    except IOError:
        have_send_list = set()

    def get_account_times(self, opener):
        resp = opener.open(self.url7)
        buf = resp.read()
        data = json.loads(re.search(r"\((\{.*\})\)", buf).group(1), encoding="gbk")
        self.logger.debug("Check whether need input captcha or not. ")
        if data["data"]["showCode"]:
            return self.get_captcha(opener)
        else:
            return "", ""

    def get_captcha(self, opener):
        tmpId =  "%d.%s"%(time.time()*1000, str(round(random.random(), 4))[2:])
        resp = opener.open(self.url6%tmpId)
        img = Image.open( StringIO(resp.read()))
        img.show()
        return raw_input("Please input captcha recognization: "), tmpId

    def send_captcha(self, opener, captcha, tmpId):
        self.logger.debug("Send captcha. ")
        url = self.url8 % (tmpId, captcha)
        req = Request(url=url, headers=self.headers)
        resp = opener.open(req)
        data = json.loads(re.search(r"\((\{.*\})\)", resp.read()).group(1), encoding="gbk")
        if data["data"] == 1:
            return tmpId, captcha

    def login(self, opener):
        url = self.url1 + urlencode(self.data)
        req = Request(url=url, headers=self.headers)
        resp = opener.open(req)
        data = json.loads(re.search(r"\((\{.*\})\)", resp.read()).group(1), encoding="gbk")
        self.logger.debug("Login first jsonp response state:%s"%data["state"])

        if data["state"] == 0:
            return "Wrong account or password. "

        req = Request(url=self.url2, headers=self.headers)
        resp = opener.open(req)
        self.logger.debug("Login second state code:%s"%resp.code)

    def get_auth_cookies(self, opener):
        while True:
            self.enter_password()
            captcha, tmpId = self.get_account_times(opener)
            if tmpId:
                while not self.send_captcha(opener, captcha, tmpId):
                    captcha, tmpId = self.get_account_times(opener)
            self.data["codeValue"] = captcha
            self.data["codeId"] = tmpId
            result = self.login(opener)
            if result:
                self.logger.info(result)
            else:
                break

    def get_search_cookies(self, opener):
        req = Request(url=self.url4, headers=self.headers)
        resp = opener.open(req)
        self.logger.debug("Finish get default search cookies, response code:%s" % resp.code)

    def search(self, opener):
        conti = True
        count = 1
        while conti:
            req = Request(url=self.url3 % count, headers=self.headers)
            self.logger.debug("Start to find girls. ")
            resp = opener.open(req)
            self.logger.debug("Search response code:%s" % resp.code)
            buf = resp.read()
            data = json.loads(re.search(r"\((\{.*\})\)", buf).group(1), encoding="gbk")
            if data["result"]:
                product_ids = set([i.split(":")[0] for i in data["result"].split(",")])
                count += 1
            elif count > 100:
                return "finished"
            else:
                raise SendMessageError("You need relogin. ")

            while True:
                try:
                    id = product_ids.pop()
                except KeyError:
                    break
                self.send_msg(opener, id)
                time.sleep(1)

    def send_msg(self, opener, id):

        s = self.have_send_list
        if id not in s:
            msg = random.choice(self.messages)
            d = quote(msg)
            url = self.url5 % (id, d)
            req = Request(url=url, headers=self.headers)
            resp = opener.open(req)
            buf = resp.read()
            recv = json.loads(re.search(r"\((\{.*\})\)", buf).group(1), encoding="gbk")
            code = recv["code"]
            self.logger.debug("Send %s to %s, status code is %s" % (msg.decode("utf-8"), id, code))
            if code == 200:
                s.add(id)
            else:
                raise SendMessageError("code: %s error: %s" % (code, recv["msg"].encode("utf-8")))
        else:
            self.logger.debug("This girl has been sent, don't molesting her any more. ")

    def pwd_input(self, msg=''):

        if msg != '':
            sys.stdout.write(msg)
        chars = []
        while True:
            newChar = getch()
            if newChar in '\3\r\n':  # 如果是换行，Ctrl+C，则输入结束
                print ''
                if newChar in '\3':  # 如果是Ctrl+C，则将输入清空，返回空字符串
                    chars = []
                break
            elif newChar == '\b' or ord(newChar) == 127:  # 如果是退格，则删除末尾一位
                if chars:
                    del chars[-1]
                    sys.stdout.write('\b \b')  # 左移一位，用空格抹掉星号，再退格
            else:
                chars.append(newChar)
                sys.stdout.write('*')  # 显示为星号
        return ''.join(chars)

    def enter_password(self):
        account = raw_input("Please input your baihe account number: ")
        self.data["txtLoginEMail"] = account
        self.data["txtLoginPwd"] = self.pwd_input("Please input your baihe account password: ")

    def enter_msg(self):
        while True:
            msg = raw_input("Please input what you want to send, input empty to break. ")
            if not msg:
                break
            else:
                try:
                    msg = msg.decode("gbk").encode("utf-8")
                except UnicodeDecodeError:
                    pass
                self.messages.append(msg)

    def start(self):
        self.enter_msg()
        cookie = LWPCookieJar()
        cookie.set_cookie(self.acc_token)
        have_load = False
        try:
            if os.path.exists(("baihe.cookie")):
                cookie.load("baihe.cookie", True, True)
                self.logger.debug("Load cookies...")
                have_load = True
            opener = build_opener(HTTPCookieProcessor(cookie))
            if not have_load:
                self.get_auth_cookies(opener)
                self.get_search_cookies(opener)
            while True:
                try:
                    if self.search(opener) == "finished":
                        self.logger.info("No more girls to send. ")
                        break
                except Exception, e:
                    time.sleep(1)
                    self.logger.error(e)
                    self.get_auth_cookies(opener)
                    self.get_search_cookies(opener)

        except KeyboardInterrupt:
            open("have_send_list.txt", "w").write(",".join(self.have_send_list))
        finally:
            self.logger.debug("Save cookies... ")
            cookie.save("baihe.cookie", True, True)


if __name__ == "__main__":
    MsgAutoSender().start()
    #MsgAutoSender().search(build_opener())


