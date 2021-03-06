# coding:utf-8
from __future__ import print_function
import gevent
from gevent import monkey;
monkey.patch_all()
import urllib2
import urllib
import os
import pickle
import re

class Downloader():
    def __init__(self, url, threadNum=3):
        self.url = url
        self.threadNum = threadNum
        self.length = self.getLength()
        self.workers = []
        self.download_info = {}
        self.speed=0

    # 从url中提取文件名
    def getFilename(self):
        # 断点续传时不再从配置文件获取文件名
        if os.path.exists("download_info1.pkl") and os.path.exists("download_info2.pkl"):
            # 读取配置文件1异常时使用备用数据，防止写入文件时关闭程序造成数据写入不完全
            try:
                f = open("download_info1.pkl", "rb")
                self.download_info = pickle.load(f)
            except:
                f = open("download_info2.pkl", "rb")
                self.download_info = pickle.load(f)
            f.close()
            filename = self.download_info["filename"]
            return filename
        # 新建的下载任务获取文件名
        url = self.url
        protocol, s1 = urllib.splittype(url)
        host, path = urllib.splithost(s1)
        filename = re.compile("([^\?]+).*").findall(path.split('/')[-1])[0]
        if '.' not in filename:
            filename = None
        print ("Filename is [%s],Do you want to change a filename?('y' or other words)" % (filename))
        answer = raw_input()
        if answer == "y" or filename is None:
            print ("Please input your new filename:")
            filename = raw_input()
        return filename

    def getLength(self):
        opener = urllib2.build_opener()
        req = opener.open(self.url)
        meta = req.info()
        length = int(meta.getheaders("Content-Length")[0])
        return length

    # 对下载包进行分片
    def get_range(self):
        ranges = []
        offset = int(int(self.length) / self.threadNum)
        for i in range(self.threadNum):
            if i == (self.threadNum - 1):
                ranges.append((i * offset, int(self.length - 1)))
            else:
                ranges.append((i * offset, (i + 1) * offset - 1))
        return ranges

    def download(self):
        filename = self.getFilename()
        task = []
        id = 1
        # 断点续传的情况,配置文件丢失时从头下载
        if os.path.exists("download_info1.pkl") and os.path.exists("download_info2.pkl") and os.path.exists(filename):
            # rb+模式打开文件时不会清掉已下载数据，并能随机读写文件
            self.file = open(filename, 'rb+')
            # 根据实际情况重置一下record字段,引入存储缓存后可能造成显示下载剩余为负的情况，目前还不知道怎么在退出时将缓存数据写入文件
            self.download_info["record"] = 0
            for ran in self.get_range():
                # 重新计算已下载数据量
                self.download_info["record"] += self.download_info[str(id)]["offset"] - self.download_info[str(id)]["start"]
                if ((self.download_info[str(id)]["offset"] - 1) < self.download_info[str(id)]["end"]):
                    #print "id:"+str(id)+"  start:"+str(self.download_info[str(id)]["start"])+"  offset:"+str(self.download_info[str(id)]["offset"])+"  end:"+str(self.download_info[str(id)]["end"])
                    theworker = worker(self, str(id))
                    task.append(gevent.spawn(theworker.process))
                id += 1
        # 从头开始下载的情况
        else:
            # 初始化字典中的已下载总量和文件名
            self.download_info["record"] = 0
            self.download_info["filename"] = filename
            # wb模式打开文件在文件不存在时能新建文件
            self.file = open(filename, 'wb')
            # 设置文件大小
            self.file.seek(self.length - 1)
            self.file.write("\0")
            # 开始将文件分片
            for ran in self.get_range():
                start, end = ran
                # 初始化字典中的各个协程的下载起始结束位置，写入文件时的偏移量
                self.download_info[str(id)] = {"start": start, "end": end, "offset": start}
                # 创建下载对象
                theworker = worker(self, str(id))
                # 下载任务加入任务列表
                task.append(gevent.spawn(theworker.process))
                id += 1
        #把监控任务加入任务列表
        task.append(gevent.spawn(self.momitor))
        # 开始用协程执行下载任务
        gevent.joinall(task)

    #打印下载进度并记录下载情况到配置文件
    def momitor(self):
        # 协程列表不为空就持续更新下载信息
        while self.workers != []:
            speed = self.speed
            #打印下载总量
            recode = self.download_info["record"]
            # 打印下载情况，speed=0时不能被除
            if (speed > 0):
                print("\r%-30s%-30s%-30s%-30s%-30s%-30s"%(u"文件大小：" + str(self.length / 1024) + " KB",
                                                            u"已下载:" + str(recode / 1024) + " KB",
                                                            u"剩余：" + str((self.length - recode) / 1024) + " KB",
                                                            u"下载速度:" + str(speed / 1024) + " KB/S",
                                                            u"完成率:" + str(float(recode * 100) / float(self.length))[0:5] + "%",
                                                            u"剩余时间:" + str((self.length - recode) / speed) + " S",),end='')
            else:
                print("\r%-30s%-30s%-30s%-30s%-30s%-30s"%(u"文件大小：" + str(self.length / 1024) + " KB",
                                                            u"已下载:" + str(recode / 1024) + " KB",
                                                            u"剩余：" + str((self.length - recode) / 1024) + " KB",
                                                            u"下载速度:0 KB/S",
                                                            u"完成率:" + str(float(recode * 100) / float(self.length))[0:5] + "%",
                                                            u"剩余时间:未知",),end='')
            self.speed=0
            # 串行方式写入两个配置文件，突然关闭程序时至少能保证一个文件已经被正常写入
            with open("download_info1.pkl", "wb") as f:
                pickle.dump(self.download_info, f)
                f.close()
            with open("download_info2.pkl", "wb") as f:
                pickle.dump(self.download_info, f)
                f.close()
            gevent.sleep(1)

        # 下载结束关闭文件流
        print (u"\n下载结束")
        # 删掉配置信息文件
        os.remove("download_info1.pkl")
        os.remove("download_info2.pkl")
        # 关闭下载文件文件流
        self.file.close()


class worker():
    def __init__(self, downloader, id):
        # 协程id
        self.id = id
        #downloader对象
        self.downloader=downloader
        # 每个协程的开始位置start，结束位置end，写入文件偏移量offset都在这个字典中
        self.workerinfo = self.downloader.download_info[self.id]
        #存储文件对象
        self.file = self.downloader.file
        # 下载地址
        self.url = self.downloader.url
        # 把自己加入到协程列表
        self.workers = self.downloader.workers
        self.workers.append(self)
        # 标记下载任务是否完成
        self.finish = False


    def process(self):
        # 如果已经下完直接退出
        if ((self.workerinfo["offset"] - 1) == self.workerinfo["end"]):
            self.finish = True
            # 从协程列表中退出
            if self in self.workers:
                self.workers.remove(self)
        req = urllib2.Request(self.url)
        buffer = 1024
        # 不下完不退出
        while (self.finish == False):
            # 构造分片请求头
            req.headers['Range'] = 'bytes=%s-%s' % (self.workerinfo["offset"], self.workerinfo["end"])
            # 发出分片请求
            f = urllib2.urlopen(req)
            try:
                while True:
                    block = f.read(buffer)
                    if not block:
                        break
                    self.file.seek(self.workerinfo["offset"])
                    self.file.write(block)
                    self.file.flush()
                    self.workerinfo["offset"] += len(block)
                    self.downloader.download_info["record"] += len(block)
                    self.downloader.speed += len(block)
                if ((self.workerinfo["offset"] - 1) < self.workerinfo["end"]):
                    raise Exception("\n协程" + self.id + "还没下完就提前结束了")
                else:
                    self.finish = True
            except Exception, e:
                # 准备重连
                gevent.sleep(5)
            finally:
                #给monitor协程有时间把下载数据更新完
                gevent.sleep(1)
                #下载完成从协程列表中退出
                if self in self.workers and self.finish == True:
                    self.workers.remove(self)


if __name__ == "__main__":
    #down = Downloader("https://wiki.onap.org/download/attachments/10780883/GMT20170713-131617_DCAE-Weekl_1920x1200.mp4?version=1&modificationDate=1500571114000&api=v2&download=true", 10)
    down = Downloader("https://mirrors.cnnic.cn/apache/hadoop/common/stable/hadoop-2.9.0.tar.gz",1)
    down.download()
