import requests
from requests.exceptions import RequestException,Timeout,ProxyError
from sqlalchemy.exc import InvalidRequestError
from lxml import etree
from app.model import PhotographyM
from app.init_db import session
from .config import userAgents
import time,os,random
from .common import Proxies
from urllib import parse
import json
s=requests.session()
s.keep_alive=False
class ScrapyPhotography(Proxies):   #摄影巴士数据
    num1=0 #设置请求次数限制
    def __init__(self,url):
        super().__init__()
        self.start_scrapy(url)

    def start_scrapy(self,url):
        self.getProxy()
        self.getRequest(url,1,None)

    def getRequest(self,url,num,proxies):
        print(proxies)
        time.sleep(random.randrange(1,4))
        urlStr=url.format(num)
        print(urlStr)
        headers={
            'Connection': 'close',
            "user-agent":userAgents[random.randrange(0,len(userAgents))]
        }
        if ScrapyPhotography.num1 > 40:
            print("请求超过40次,请稍后再次请求!")
            return False
        if proxies in self.no_ipproxy:
            proxies=self.randipproxy()

        try:
            req=s.get(urlStr,headers=headers,proxies=proxies,timeout=2)
            content=req.text
            ele=etree.HTML(content)
            postlist_ele=ele.xpath("//div[@class='postlist']")
            if req.status_code == 200 and len(postlist_ele) != 0:
                for ele_item in postlist_ele:
                    imgurl=ele_item.xpath("div[@class='post_img']/a/img/@src")[0].replace("h=150&w=200","h=600&w=800")
                    title=ele_item.xpath("div[@class='post_con']/h2/a/text()")[0]
                    author="摄影构图学"
                    desc=ele_item.xpath("div[@class='post_con']/p")[1].xpath("./text()")[0]
                    detailurl=ele_item.xpath("div[@class='post_con']/a[@class='more-link']/@href")[0]
                    idStr = self.saveMysql(title, author, desc)
                    self.savePic(imgurl,proxies,idStr)
                    self.scrapyDetail(detailurl,proxies,idStr)
                num=num+1
                self.getRequest(url,num,proxies)
            else:
                return False

        except ProxyError:
            print("代理Error: %r" % ProxyError)
            ScrapyPhotography.num1+=1
            self.no_ipproxy.append(proxies)
            self.getRequest(url,num,self.randipproxy())
        except Timeout:
            print("超时Error: %r" % Timeout)
            ScrapyPhotography.num1+=1
            self.no_ipproxy.append(proxies)
            self.getRequest(url,num,self.randipproxy())
        except Exception as err:
            print("未知Error: %r" % err)
            ScrapyPhotography.num1+=1
            self.no_ipproxy.append(proxies)
            self.getRequest(url,num,self.randipproxy())

    def scrapyDetail(self,detailurl,proxies,id):
        headers={
            'Connection': 'close',
            "user-agent":userAgents[random.randrange(0,len(userAgents))]
        }
        req=s.get(detailurl,headers=headers,proxies=proxies,timeout=2)
        htmlStr=req.text
        ele=etree.HTML(htmlStr)
        content_ele=ele.xpath("//div[@class='post-content']/div")[0].xpath("p")
        content_str="<div>"
        for ele_item in content_ele:
            content_str=content_str+str(etree.tostring(ele_item,encoding="utf-8",method="HTML",pretty_print=True),encoding = "utf8")
        content_str+'</div>'
        try:
            Photography = session.query(PhotographyM).filter(PhotographyM.id == id).all()
            if len(Photography) != 0:
                Photography[0].content=content_str
                session.commit()
        except InvalidRequestError:
            print("更新Error: %r" % InvalidRequestError)
            session.rollback()
        except Exception as err:
            print("Mysql2未知Error: %r" % err)
            session.rollback()


    def savePic(self,imgcover,proxies,id):
        basedir=os.path.dirname(__file__)
        hostpath=parse.urlparse(imgcover)
        imgpathlist=hostpath[4].split("/")
        imgname=imgpathlist[len(imgpathlist)-1].split("&")[0]
        imgpath=os.path.abspath(os.path.join(basedir,'..','..','static','photography',"/".join(imgpathlist[3:5])))
        headers={
            'Connection': 'close',
            "user-agent":userAgents[random.randrange(0,len(userAgents))]
        }
        if not os.path.exists(imgpath):
            print("路径不存在,正在创建路径~~~~~~")
            os.makedirs(imgpath)
        try:
            res=s.get(imgcover,headers=headers,proxies=proxies,timeout=2)
            with open(os.path.join(imgpath,imgname),"wb") as fp:
                fp.write(res.content)
                fp.close()
                try:
                    query=session.query(PhotographyM).filter(PhotographyM.id==id).all()[0]
                    imgurl='/static/photography/{0}/{1}'.format("/".join(imgpathlist[3:5]),imgname)
                    query.imgurlstr=imgurl
                    session.commit()
                except InvalidRequestError as err:
                    print("InvalidRequestError %r" % repr(err))
                    session.rollback()
                except Exception as e:
                    print("Exception %r" % repr(e))
                    session.rollback()
        except Exception as err:
            print("图片下载Error:{0}".format(err))

    def saveMysql(self,title,author,desc):
        try:
            insert_sql = PhotographyM(title,author,desc)
            session.add(insert_sql)
            session.commit()
            return insert_sql.id
        except InvalidRequestError:
            print("插入Error: %r" % InvalidRequestError)
            session.rollback()
        except Exception as err:
            print("Mysql3未知Error: %r" % err)
            session.rollback()
# ScrapyPhotography("http://www.fsbus.com/page/{0}/")
