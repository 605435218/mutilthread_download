#coding:utf-8
import gevent
from gevent import monkey;monkey.patch_all()
import urllib2
import urllib
import os

class Downloader():
    def __init__(self, url,threadNum=3):
        self.url = url
        self.threadNum = threadNum
        self.length = self.getLength()
        self.workers=[]
        self.download_bak={}


    def getFilename(self):
        url = self.url
        protocol, s1 = urllib.splittype(url)
        host, path = urllib.splithost(s1)
        filename = path.split('/')[-1]
        if '.' not in filename:
            filename = None
        print "Do you want to change a filename?('y' or other words)"
        answer = raw_input()
        if answer == "y" or filename is None:
            print "Please input your new filename:"
            filename = raw_input()
        return filename

    def getLength(self):
        opener = urllib2.build_opener()
        req = opener.open(self.url)
        meta = req.info()
        length = int(meta.getheaders("Content-Length")[0])
        return length

    #对下载包进行分片
    def get_range(self):
        ranges = []
        offset = int(int(self.length) / self.threadNum)
        for i in range(self.threadNum):
            if i == (self.threadNum - 1):
                ranges.append((i*offset,int(self.length-1)))
            else:
                ranges.append((i*offset,(i+1)*offset-1))
        return ranges

    def download(self):
        filename = self.getFilename()
        task=[]
        id=1
        if os.path.exists(filename):
            self.file=open(filename, 'rb+')
        else:
            self.file = open(filename, 'wb+')
        #设置文件结尾
        self.file.seek(self.length-1)
       # self.file.write("\0")
        for ran in self.get_range():
            start, end = ran
            theworker=worker(self,id,start,end)
            id+=1
            task.append(gevent.spawn(theworker.process))
        task.append(gevent.spawn(self.momitor))
        gevent.joinall(task)


    def momitor(self):
        recode = 0
        while self.workers!=[]:
            speed=0
            #统计下载速度
            for worker in self.workers:
                speed += worker.speed
                worker.speed = 0
            #记录下载总量
            recode += speed
            #打印下载情况
            if(speed>0):
                print "\r%-40s%-40s%-40s%-40s%-40s" % ("文件大小："+str(self.length/1024)+"KB",
                                      "已下载:"+str(recode/1024)+"KB",
                                      "剩余："+str((self.length-recode)/1024)+"KB",
                                      "下载速度:"+str(speed/1024)+"KB/S",
                                      "剩余时间:"+str((self.length-recode)/speed)+" S  当前协程数"+str(len(self.workers))),
            else:
                print "\r%-40s%-40s%-40s%-40s%-40s" % ("文件大小："+str(self.length/1024)+"KB",
                                      "已下载:"+str(recode/1024)+"KB",
                                      "剩余："+str((self.length-recode)/1024)+"KB",
                                      "下载速度:"+str(speed/1024)+"KB/S",
                                      "剩余时间:未知"+"   当前协程数"+str(len(self.workers))),
            gevent.sleep(1)
        #下载结束关闭文件流
        print "\n下载结束"
        self.file.close()

class worker():
    def __init__(self,downloader,id,start,end):
        self.id=id
        self.start=start
        self.end=end
        self.downloader = downloader
        self.file=self.downloader.file
        #写入文件的偏移量
        self.offset=start
        #当前协程的下载速度
        self.speed=0
        #下载地址
        self.url=self.downloader.url
        #把自己加入到协程列表
        self.workers=self.downloader.workers
        self.workers.append(self)
        self.finish=False
        print "\n协程" + str(self.id) + "下载开始，开始位置:" + str(self.start) + "结束位置:" + str(self.end)

    def process(self):
        req = urllib2.Request(self.url)
        buffer = 1024*10
        #不下完不退出
        while(self.finish==False):
            # 构造分片请求头
            req.headers['Range'] = 'bytes=%s-%s' % (self.offset, self.end)
            # 发出分片请求
            f = urllib2.urlopen(req)
            try:
                while True:
                    block = f.read(buffer)
                    if not block:
                        break
                    self.file.seek(self.offset)
                    self.file.write(block)
                    self.offset = self.offset + len(block)
                    self.speed+=len(block)
                if((self.offset-1)<self.end):
                    raise Exception("\n协程"+str(self.id)+"还没下完就提前结束了")
                else:
                    print "\n协程"+str(self.id)+"下载结束，开始位置:"+str(self.start)+"结束位置:"+str(self.end)+"实际结束位置： "+str(self.offset-1)
                    self.finish=True
                    #从协程列表中退出
                    if self in self.workers:
                        self.workers.remove(self)
            except Exception, e:
               # print e.message
                #准备重连
                gevent.sleep(3)





if __name__ == "__main__":
    #down=Downloader("http://download.jetbrains.8686c.com/cpp/CLion-2017.3.1.tar.gz",10)
    #down=Downloader("http://haixi.sfkcn.com:8080/201508/books/junit_sz2_jb51.rar",10)
    down=Downloader("http://fhnw.fiberhome.com/images/%E6%B5%B7%E5%A4%96.jpg",1)
    down.download()



'''
f=open('1.txt','rb+')
f.seek(6)
f.write("1")
f.flush()
f.seek(7)
f.write("2")
f.flush()
f.seek(8)
f.write("3")
f.flush()

f.seek(3)
f.write("4")
f.flush()
f.seek(4)
f.write("5")
f.flush()
f.seek(5)
f.write("6")
f.flush()

f.seek(0)
f.write("7")
f.flush()
f.seek(1)
f.write("8")
f.flush()
f.seek(2)
f.write("9")
f.flush()

f.seek(12)
f.write("666")
f.flush()
'''
'''
def test1():
    f.seek(6)
    f.write("1")
    f.flush()
    gevent.sleep(0)
    f.seek(7)
    f.write("2")
    f.flush()
    gevent.sleep(0)
    f.seek(8)
    f.write("3")
    f.flush()


def test2():
    f.seek(3)
    f.write("4")
    f.flush()
    gevent.sleep(0)
    f.seek(4)
    f.write("5")
    f.flush()
    gevent.sleep(0)
    f.seek(5)
    f.write("6")
    f.flush()


def test3():
    f.seek(0)
    f.write("7")
    f.flush()
    gevent.sleep(0)
    f.seek(1)
    f.write("8")
    f.flush()
    gevent.sleep(0)
    f.seek(2)
    f.write("9")
    f.flush()



gevent.joinall(
    [gevent.spawn(test1), gevent.spawn(test2)]
)
gevent.spawn(test3).join()
f.close()
'''


#with open("abc.pkl", "wb") as f:
#    dic = {"age": 23, "job": "student"}
#    pickle.dump(dic, f)
# 反序列化
#with open("abc.pkl", "rb") as f:
#    aa = pickle.load(f)
#    print(aa)
#    print(type(aa))