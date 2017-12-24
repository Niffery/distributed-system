import socketserver as sose
import socket
import threading
from random import randrange
from time import sleep
import sys
#need a file for configuration of port and ip address
GlobalLock=threading.Lock()
event=threading.Event()

class entity():
    def __init__(self,i):
        self.bankaccount=1000 #initial money           
        self.clientid=i#and which line of the file it should read
        self.onmarker=[False,False,False]#which marker is placing on me
        self.recordmoney=[1000,1000,1000]#respectively for marker0,1,2
        self.receivemarker=[{},{},{}]#for marker0, receivedmarker[0]={i:True}:i is Clientid,indicate I have received subsequent marker0,initiated as all false
        self.channelstate=[{},{},{}]#for marker0,channelstate[0]={i:[True/False,...]}
        for i in range(0,len(self.receivemarker)):
            for j in range(0,len(self.receivemarker)):
                if j!=self.clientid:
                    self.receivemarker[i][j]=False
        for i in range(0,len(self.channelstate)):
            for j in range(0,len(self.channelstate)):
                if j!=self.clientid:
                    self.channelstate[i][j]=[False]
        #the index of channelstate indicate marker from which client should be influenced
        #the dict:{channelid[True/False indicate whether this channel should record...state of the channel],}
    def Transfer(self,communication): #amount is the amount of money transferred
        while True:
            if event.is_set():
                break
            sleep(2)
            amount=randrange(2,10)
            if amount<=7:
                continue
            GlobalLock.acquire()
            self.bankaccount-=amount
            receiver=randrange(0,len(communication.sendsocks))
            communication.sendsocks[receiver].send('Transfer {} dollars from Client {}'.format(amount,self.clientid).encode())
            GlobalLock.release()

    def ReceiveMoney(self,data):
        GlobalLock.acquire()
        tmplist=data.split(' ')
        amount=int(tmplist[1])
        From=int(tmplist[5])
        self.bankaccount+=amount
        for i in range(0,len(self.channelstate)):
            if self.onmarker[i]==True and self.receivemarker[i][From]==False and self.channelstate[i][From][0]==True:
                self.channelstate[i][From].append("Receive {} dollars from Client {}".format(amount,From))
        GlobalLock.release()
        
    def InitiateMarker(self,communication):
        GlobalLock.acquire()
        self.recordmoney[self.clientid]=self.bankaccount
        self.onmarker[self.clientid]=True
        for key in self.receivemarker[self.clientid].keys():
            self.receivemarker[self.clientid][key]=False
        for key in self.channelstate[self.clientid].keys():
            self.channelstate[self.clientid][key]=[True]
        for i in range(0,len(communication.sendsocks)):
            communication.sendsocks[i].send('Marker {} from {}'.format(self.clientid,self.clientid).encode())
        GlobalLock.release()
        
    def ReceiveMarker(self,data,communication):
        GlobalLock.acquire()
        tmplist=data.split(' ')
        Markerid=int(tmplist[1])
        From=int(tmplist[3])
        if Markerid==From:
            self.onmarker[Markerid]=True
            self.receivemarker[Markerid][From]=True
            self.recordmoney[Markerid]=self.bankaccount
            for key in self.channelstate[Markerid].keys():
                if key==From:
                    self.channelstate[Markerid][key]=[False] 
                self.channelstate[Markerid][key]=[True]
            symbol=True
            for key in self.receivemarker[Markerid].keys():
                if self.receivemarker[Markerid][key]==False:
                    symbol=False
            if symbol==True:
                #print the snapshot info and clear all saved states
                print("Marker {}:".format(Markerid))
                print("Current money:${}".format(self.recordmoney[Markerid]))
                print("Channel states:")
                for key in self.channelstate[Markerid].keys():
                    print("Channel from Client {}:{}".format(key,self.channelstate[Markerid][key]))
                self.onmarker[Markerid]=False
                for key in self.receivemarker[Markerid].keys():
                    self.receivemarker[Markerid][key]=False
                for key in self.channelstate[Markerid].keys():
                    self.channelstate[Markerid][key]=[False]
            GlobalLock.release()
            sleep(3)
            for i in range(0,len(communication.sendsocks)):
                communication.sendsocks[i].send('Marker {} from {}'.format(Markerid,self.clientid).encode())
        else:
            self.receivemarker[Markerid][From]=True
            for key in self.channelstate[Markerid].keys():
                self.channelstate[Markerid][key][0]=False
            symbol=True
            for key in self.receivemarker[Markerid].keys():
                if self.receivemarker[Markerid][key]==False:
                    symbol=False
            if symbol==True:
                #print the snapshot info and clear all saved states
                print("Marker {}:".format(Markerid))
                for key in self.channelstate[Markerid].keys():
                    if len(self.channelstate[Markerid][key])>1:
                        for i in range(1,len(self.channelstate[Markerid][key])):
                            self.recordmoney[Markerid]-=int(self.channelstate[Markerid][key][i].split(' ')[1])
                print("Current money:${}".format(self.recordmoney[Markerid]))
                print("Channel states:")
                for key in self.channelstate[Markerid].keys():
                    print("Channel from Client {}:{}".format(key,self.channelstate[Markerid][key]))
                self.onmarker[Markerid]=False
                for key in self.receivemarker[Markerid].keys():
                    self.receivemarker[Markerid][key]=False
                for key in self.channelstate[Markerid].keys():
                    self.channelstate[Markerid][key]=[False]
                
            GlobalLock.release()
            

    
class Communication():
    def __init__(self,addresslist,i): #addresslist consists of its own address and others' listening addresses
        self.server=ThreadedTCPServer(addresslist[i],ServerHandler)
        self.listenaddress=addresslist[i]#serveraddress of my own
        self.sendsocks=[]
        self.thread=threading.Thread(target=self.server.serve_forever)
        self.sendaddress=[]
    def CreateSockets(self,addresslist,message):#address is a tuple of ip address and port
        for i in range(0,5):
            if addresslist[i]!=self.listenaddress and not (addresslist[i] in self.sendaddress):
                try:
                    sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                    sock.connect(addresslist[i])
                except Exception as e:
                    print(e)
                else:
                    self.sendsocks.append(sock)
                    self.sendaddress.append(addresslist[i])
                    sock.send(message.encode())

        
class ServerHandler(sose.BaseRequestHandler):
    def handle(self):
        while True:
            conn=self.request
            addr=self.client_address
            while True:
                if event.is_set():
                    break
                data=str(conn.recv(1024),encoding='utf8')
                print(data)
                if data.startswith('Newprocess'):
                    communication.CreateSockets(serveraddress,"Analog from process{}".format(Account.clientid))
                elif data.startswith('Transfer'):
                    Account.ReceiveMoney(data[:32])       
                elif data.startswith('Marker'):
                    Account.ReceiveMarker(data[:15],communication)
            if event.is_set():
                conn.close()
                communication.server.shutdown()
                communication.server.server_close()
                break
            

class ThreadedTCPServer(sose.ThreadingMixIn, sose.TCPServer):
    pass

if __name__=='__main__':
    script,clientid=sys.argv 
    serveraddress=[]
    with open('configuration.txt','r') as file:
        for i in range(0,5):
            tmpstr=file.readline().strip()
            serveraddress.append((tmpstr.split(' ')[0],int(tmpstr.split(' ')[1])))
            
    Account=entity(int(clientid))
    communication=Communication(serveraddress,int(clientid))
    communication.thread.start()
    sleep(1)
    communication.CreateSockets(serveraddress,'Newprocess from process{}'.format(Account.clientid))

    Transferthread=threading.Thread(target=Account.Transfer,args=(communication,))
    sleep(5)
    Transferthread.start()
    while True:
        command=input("Enter your command:\n")
        if command=='exit':
            event.set()
            while Transferthread.is_alive():
                pass
            while communication.thread.is_alive():
                pass
            exit(0)
        if command=='take':
            Account.InitiateMarker(communication)

           
