import socketserver as sose
import socket
import sys
import threading
from random import randrange
from time import sleep
import datetime

lamport=None
Lock1=threading.Lock()
Lock2=threading.Lock()
filetoopen='testcontent.txt'
class Lamport_Client():
    def __init__(self,processid,port):
        self.processid=processid
        self.numOfLikes=0
        self.LamportClock=datetime.datetime.strptime(datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S'),'%Y-%m-%d-%H-%M-%S')
        self.port=port
        self.sendsocks=[]
        self.sendaddress=[]
        self.recvsocks=[]
        self.requestQueue=[]
        self.replyQueue=[]
        

    def createsocks(self,message):
        for i in range(0,5):
            address=('127.0.0.1',30000+i)
            if address[1]!=self.port and not(address in self.sendaddress):
                try:
                    sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                    sock.connect(address)
                except Exception as e:
                    print (e)
                else:
                    self.sendsocks.append(sock)
                    self.sendaddress.append(address)
                    sock.send(message.encode())#message used to indicate whether its newly created process or just
                    #continue

    def _queuesort(self):
        if len(self.requestQueue)>1:
            for j in range(len(self.requestQueue)-1,-1,-1):
                for i in range(1,j+1):
                    if abs((self.requestQueue[i-1][0]-self.requestQueue[i][0]).total_seconds())<=20:
                        if self.requestQueue[i-1][1]>self.requestQueue[i][1]:
                            self.requestQueue[i-1],self.requestQueue[i]=self.requestQueue[i],self.requestQueue[i-1]
                    elif self.requestQueue[i-1][0]>self.requestQueue[i][0]:
                        self.requestQueue[i-1],self.requestQueue[i]=self.requestQueue[i],self.requestQueue[i-1]

    def addrequest(self,*pair):
        Lock1.acquire()
        try:
            for i in range(0,len(self.requestQueue)):
                if pair[0][1]==self.requestQueue[i][1]: return False
            self.requestQueue.append(*pair)
            self._queuesort()
            print(self.requestQueue,'I am adding!')
            return True
        
        finally:
            Lock1.release()

    def sendrequest(self):
        Lock2.acquire()
        tmpstr=datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S')
        self.LamportClock=datetime.datetime.strptime(tmpstr,'%Y-%m-%d-%H-%M-%S')
        boo=self.addrequest((self.LamportClock,self.processid))
        Lock2.release()
        if(boo):
            for i in range(0,len(self.sendsocks)):
                requeststr='Request:{}:{}'.format(self.LamportClock.strftime('%Y-%m-%d-%H-%M-%S'),self.processid)
                self.sendsocks[i].sendall(requeststr.encode())

    def sendreply(self,requestinfo):
        
        sleep(4)
        send_data=bytes('Reply:{}'.format(self.processid),encoding='utf8')
        for i in range(0,len(self.sendaddress)):
            if int(requestinfo[2])+30000==self.sendaddress[i][1]:
                self.sendsocks[i].sendall(send_data)
                break
        

    def repliedall(self):
        try:
            Lock1.acquire()
            return len(self.replyQueue)==len(self.sendaddress)
            
        finally:
            Lock1.release()
        
    def replydeal(self,data):
        
        sleep(4)
        if data not in self.replyQueue:
            Lock2.acquire()
            self.replyQueue.append(data)
            Lock2.release()
        if self.ranking()==0 and self.repliedall():
            self.Readable()
        
        
    def releasedeal(self,data):
        
        try:
            Lock2.acquire()
            requestinfo=data.split(':')
            for i in range(0,len(self.requestQueue)):
                if int(requestinfo[2])==self.requestQueue[i][1]:
                    self.requestQueue.pop(i)
                    break
        except IndexError as e:
            print(e,' is ok')
        else:
            if self.ranking()==0 and self.repliedall():
                lamport.Readable()
        finally:
            Lock2.release()
        
    def ranking(self):
        try:
            Lock1.acquire()
            if len(self.requestQueue)==0:
                return -1
            for i in range(0,len(self.requestQueue)):
                if self.processid==self.requestQueue[i][1]: return i
        finally:
            Lock1.release()
        
    def Readable(self):
        Lock1.acquire()
        print(self.requestQueue)
        print('process{} am runing'.format(self.processid))
        with open(filetoopen,'r+') as f:
           line=f.readline()
           print(line)
           f.seek(0)
           content=line.rsplit(':',1)
           print("Current numOfLike is ",content[1])
           newnum=randrange(1,3)+int(content[1])
           self.numOfLikes=newnum
           print("Process{} Like {}".format(self.processid,self.numOfLikes))
           f.write("\"CONTENT FROM PROCESS{}\"Like:{}".format(lamport.processid,newnum))
           
        self.requestQueue.pop(0)
        self.replyQueue.clear()
        releasestr='Release:process:{}'.format(self.processid)
        for i in range(0,len(self.sendsocks)):
            self.sendsocks[i].sendall(releasestr.encode())
        Lock1.release()
    
        
class MyServerHandler(sose.BaseRequestHandler):      
    def handle(self):
        while True:
            conn=self.request
            addr=self.client_address
            while True:
                data=str(conn.recv(1024),encoding='utf8')
                print(data)
                if data.startswith('Newprocess'):
                    lamport.recvsocks.append(self.request)
                    lamport.createsocks("Analog from process{}".format(lamport.processid))
                elif data.startswith('Request'):
                    Lock2.acquire()
                    requestinfo=data.split(':')
                    timestamp=datetime.datetime.strptime(requestinfo[1],('%Y-%m-%d-%H-%M-%S'))
                    lamport.addrequest((timestamp,int(requestinfo[2])))
                    Lock2.release()
                    lamport.sendreply(requestinfo)
                elif data.startswith('Reply'):
                    lamport.replydeal(data)
                elif data.startswith('Release'):
                    
                    lamport.releasedeal(data)
            conn.close()


class ThreadedTCPServer(sose.ThreadingMixIn, sose.TCPServer):
    pass


if __name__=='__main__':

    script,first=sys.argv
    ip,port='127.0.0.1',30000+int(first)
    lamport=Lamport_Client(int(first),30000+int(first))
    server=ThreadedTCPServer((ip,port),MyServerHandler)
    server_thread=threading.Thread(target=server.serve_forever)
    server_thread.start()
    sleep(1)
    lamport.createsocks('Newprocess from process{}'.format(lamport.processid))
    while True:
        
        ss=input("enter something:\n")
        if ss=='a': break#this way of exiting doesn't work here, will raise an exception and block the process
        elif ss=='request':
            lamport.sendrequest()
        elif ss=='print':
            print(lamport.requestQueue,'\n',lamport.replyQueue)
    server.shutdown()
    server.server_close()
