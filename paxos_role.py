import threading
import sys
from time import *
import socketserver as sose
import socket

GlobalLock=threading.Lock()

class ThreadedTCPServer(sose.ThreadingMixIn,sose.TCPServer):
        pass

class ServerHandler(sose.BaseRequestHandler):
	def handle(self):
		while True:
			conn=self.request
			addr=self.client_address
			while True:
				data=str(conn.recv(1024),encoding='utf8')
				if not data:
					break
				print(data)
                                #print(addr,type(addr))
				if data.startswith("Newprocess"):
					communication.create_connection("Analog from {}".format(communication.hostaddr))
				if data.startswith("Restore"):
					communication.update_connection("Update from {}".format(communication.hostaddr),addr[0])
				elif data.startswith("Heartbeat"):
					kiosk.get_heartbeat(addr[0])
				elif data.startswith("Election"):
					kiosk.receive_election(addr[0],data)
				elif data.startswith("Vote"):
					kiosk.receive_vote(data)
				elif data.startswith("ACK"):
					kiosk.receive_ack(data)
				elif data.startswith("Accept"):
					kiosk.receive_accept(data)
				elif data.startswith("Recover"):
					kiosk.receive_recover(addr[0])
				elif data.startswith("Tickets"):
					kiosk.receive_ticket(data)
				elif data.startswith("Propose"):
					kiosk.receive_propose(data)
			conn.close()
			break
class Communication():
	def __init__(self):
		self.hostaddr=socket.gethostbyname(socket.gethostname())
		self.addresslist=[]
		with open("configuration.txt","r") as file:
			for i in range(5):
				tmp=file.readline().strip().split(' ')
				self.addresslist.append((tmp[0],int(tmp[1])))
		self.server=ThreadedTCPServer((self.hostaddr,5001),ServerHandler)
		self.sendsocks=[]
		self.thread=threading.Thread(target=self.server.serve_forever)
		self.sendaddress=[]
	def create_connection(self,message):
		i=0
		GlobalLock.acquire()
		while i<len(self.sendsocks):
			try:
				print("testing for",self.sendsocks[i])
				self.sendsocks[i].send("test".encode())
				
			except Exception as e:	
				print(e)
				self.sendaddress.remove(self.sendaddress[i])
				self.sendsocks.remove(self.sendsocks[i])
				continue
			else:
				i+=1
				continue
		GlobalLock.release()

		for i in range(0,5):
			if self.addresslist[i][0]!=self.hostaddr and not\
			self.addresslist[i][0] in self.sendaddress:
				try:
					sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
					sock.connect(self.addresslist[i])
				except Exception as e:
					print(e)
				else:
					GlobalLock.acquire()
					self.sendsocks.append(sock)
					self.sendaddress.append(self.addresslist[i][0])
					sock.send(message.encode())
					GlobalLock.release()
	def update_connection(self,message,addr):
		GlobalLock.acquire()
		for i in range(len(self.sendaddress)):
			if self.sendaddress[i]==addr:
				self.sendaddress.remove(self.sendaddress[i])
				self.sendsocks.remove(self.sendsocks[i])
				break
		try:
			sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
			sock.connect((addr,5001))
		except Exception as e:
			print(e)
		else:
			self.sendsocks.append(sock)
			self.sendaddress.append(addr)
			sock.send(message.encode())
		GlobalLock.release()

communication=Communication()

def timer_func():
	if kiosk.leader_role==False and kiosk.receive_heartbeat==True:
		GlobalLock.acquire()
		kiosk.receive_heartbeat=False
		print("receiving heartbeat")
		GlobalLock.release()
			
	elif kiosk.leader_role==False and kiosk.receive_heartbeat==False:
		print("It's 10 seconds since I last received heartbeat\
			,maybe we should start election")
		GlobalLock.acquire()
		if kiosk.leader_addr!=None:
			kiosk.known_nodes-=1
			kiosk.leader_addr=None
			kiosk.election=False
		GlobalLock.release()
		kiosk.start_election()
	global timer
	timer =threading.Timer(10,timer_func)
	timer.start()

timer=threading.Timer(11,timer_func)#remember to edit the time interval

class paxos():
	def __init__(self):
		self.receive_heartbeat=False
		self.processid=0#should be passed in to decide priority when choosing leader
		self.start_propose=[]#used to currently propose,format:log_index num,some info
		self.cur_tickets=100
		self.leader_role=False#0 I'm not leader,1 I am
		self.election=False#whether I started a election
		self.known_nodes=3#majority can be calculated through this num of all nodes\
		self.majority=2
		self.log_index=-1
		self.leader_addr=None
		self.log_record=[]#format:index_num,buy.. tickets
		self.receive_votes=1#i will always vote to myself
				#in our election,a leader should receive all other process's agree
				# because we can totally order, log more complete, processid smaller is highest
		self.heartbeat_thread=threading.Thread(target=self.send_heartbeat)
		self.heartbeat_symbol=True#indicate whether the heartbeat should still run
	def save(self):
		GlobalLock.acquire()
		with open("record.txt","w") as file1:
			file1.write("{}\n".format(self.cur_tickets))
			#file1.write("{}\n".format(self.leader_role))
			file1.write("{}\n".format(self.log_index))
			#file1.write("{}\n".format(self.leader_addr))
		with open("log.txt","w") as file2:
			for i in range(len(self.log_record)):
				file2.write(self.log_record[i]+'\n')
		GlobalLock.release()
	def restore(self):
		try:
			file1=open("record.txt","r")
			file2=open("log.txt","r") 
		except Exception as e:
			print(e)
			return False #first time
		else:
			self.cur_tickets=int(file1.readline().strip())
			#self.leader_role=bool(file1.readline().strip())
			self.log_index=int(file1.readline().strip())
			#self.leader_addr=file1.readline().strip()
			while True:
				tmp=file2.readline().strip()
				if tmp=='':
					break
				self.log_record.append(tmp)
			file1.close()
			file2.close()
			return True #recovered

	def start_election(self):
		if self.election==True:
			return
		i=0
		GlobalLock.acquire()
		print("I'm starting election")
		self.election=True
		self.received_votes=1
		GlobalLock.release()
		while i<len(communication.sendsocks):
			try:
				communication.sendsocks[i].send(\
				"Election:{}:{}".format(len(self.log_record),self.processid).encode())
			except Exception as e:
				GlobalLock.acquire()
				print(e)
				communication.sendsocks.remove(communication.sendsocks[i])
				communication.sendaddress.remove(communication.sendaddress[i])
				#self.known_nodes-=1
				GlobalLock.release()
			else:
				i+=1
				continue
				

	def receive_election(self,addr,data):#this addr is (ip,port) I suppose,actually can only pass in ip
		#for node who is not qualified send reject data should startwith "Vote"
		tmp=data.split(":")#length of logrecord,and processid
		received_length,received_id=int(tmp[1]),int(tmp[2])
		sock=None
		for i in range(len(communication.sendaddress)):
			if communication.sendaddress[i]==addr:
				sock=communication.sendsocks[i]
				break	
		if received_length>len(self.log_record):#this guy can be leader as least to me
			sock.send("Vote:ACK:{}".format(self.processid).encode())
		elif received_length==len(self.log_record) and received_id<self.processid:
			sock.send("Vote:ACK:{}".format(self.processid).encode())
		else:
			sock.send("Vote:REJ:{}".format(self.processid).encode())

	def receive_vote(self,data):#anything startswith Vote
		tmp=data.split(":")
		GlobalLock.acquire()
		if self.election==True:
			if tmp[1]=="ACK":
				self.received_votes+=1
				if self.received_votes>=self.known_nodes:
					#now I'm the leader
					self.leader_role=True
					self.election=False
					self.leader_addr=None
					print("begin sending heartbeat")
					#self.heartbeat_thread.start()
					#the thread of sending heartbeat starts
				GlobalLock.release()
			elif tmp[1]=="REJ":
				self.leader_role=False
				self.election==False
				self.received_votes=1
				GlobalLock.release()

	def send_heartbeat(self):
		while self.heartbeat_symbol==True:
			if self.leader_role==True:
				i=0
				while i<len(communication.sendsocks):		
					try:
						communication.sendsocks[i].send("Heartbeat".encode())
					except Exception as e:
						GlobalLock.acquire()
						print(e)
						communication.sendsocks.remove(communication.sendsocks[i])
						communication.sendaddress.remove(communication.sendaddress[i])
						GlobalLock.release()
						continue
					else:
						i+=1
						continue
			sleep(3)

	def get_heartbeat(self,addr):
		GlobalLock.acquire()
		self.receive_heartbeat=True
		if self.leader_role==False:
			self.leader_addr=addr
			self.leader_role=False			
		GlobalLock.release()
	
	def recover(self):
		for i in range(len(communication.sendsocks)):
			if communication.sendaddress[i]==self.leader_addr:
				communication.sendsocks[i].send("Recover".encode())
				break

	def receive_recover(self,addr):
		GlobalLock.acquire()
		print("I sent tickets")
		for i in range(len(communication.sendsocks)):
			if communication.sendaddress[i]==addr:
				print("sending tickets")
				communication.sendsocks[i].send("Tickets:{}".format(self.cur_tickets).encode())
				break
		GlobalLock.release()
	def receive_ticket(self,data):
		tmp=data.split(":")
		print("received tickets")
		GlobalLock.acquire()
		self.cur_tickets=int(tmp[1])
		GlobalLock.release()

	def propose(self,numoftickets):
		if self.leader_role==False and self.leader_addr!=None:
			for i in range(len(communication.sendsocks)):
				if communication.sendaddress[i]==self.leader_addr:
					communication.sendsocks[i].send("Propose:{}".format(numoftickets).encode())
					break
		elif self.leader_role==True:
			GlobalLock.acquire()
			print("start propose from leader")
			self.log_index+=1
			self.start_propose.append([self.log_index,1,numoftickets])#log_index,received ack,ticketsnum
			GlobalLock.release()
			i=0
			while i<len(communication.sendsocks):
				try:
					communication.sendsocks[i].send("Propose:{}:{}".format(self.log_index,numoftickets).encode())
				except Exception as e:
					GlobalLock.acquire()
					print(e)
					communication.sendsocks.remove(communication.sendsocks[i])
					communication.sendaddress.remove(communication.sendaddress[i])
					GlobalLock.release()
					continue
				else:
					i+=1
					continue

	def receive_propose(self,data):#only received by non-leader
		tmp=data.split(":")
		if len(tmp)==2:
			self.propose(int(tmp[1]))
		elif len(tmp)==3:
			for i in range(len(communication.sendaddress)):
				if self.leader_addr==communication.sendaddress[i]:
					communication.sendsocks[i].send("ACK:{}".format(tmp[1]).encode())
					break
	def receive_ack(self,data):
		tmp=data.split(":")
		GlobalLock.acquire()
		for i in range(len(self.start_propose)):
			if int(tmp[1])==self.start_propose[i][0]:
				self.start_propose[i][1]+=1
				if self.start_propose[i][1]>=self.majority:
					for j in range(len(communication.sendsocks)):
						communication.sendsocks[j].send("Accept:{}:{}"\
						.format(self.start_propose[i][0],self.start_propose[i][2]).encode())
					self.log_record.append("Index{}:buy {} tickets".format(self.start_propose[i][0],self.start_propose[i][2]))
					self.cur_tickets-=self.start_propose[i][2]	
					self.start_propose.remove(self.start_propose[i])
					break
		GlobalLock.release()
	def receive_accept(self,data):
		tmp=data.split(":")
		GlobalLock.acquire()
		self.log_record.append("Index{}:buy {} tickets".format(tmp[1],tmp[2]))
		self.cur_tickets-=int(tmp[2])
		self.log_index=int(tmp[1])
		GlobalLock.release()

if __name__=='__main__':
	_,processid=sys.argv
	kiosk=paxos()
	p=kiosk.restore()
	kiosk.processid=int(processid)

	communication.thread.start()
	sleep(1)
	if p==True:#recovered process
		communication.create_connection("Restore process from {}".format(communication.hostaddr))
	elif p==False:#first time as new process
		communication.create_connection("Newprocess from {}".format(communication.hostaddr))
	
	sleep(3)
	timer.start()
	kiosk.heartbeat_thread.start()
	while True:
		command=input("enter something:")
		if command.startswith("buy"):
			kiosk.propose(int(command.split(" ")[1]))
		if command=="exit":
			communication.server.shutdown()
			communication.server.server_close()
			timer.cancel()
			kiosk.heartbeat_symbol=False
			#kiosk.save()
			exit(0)
		if command=="recover":
			kiosk.recover()
		if command=="save":
			kiosk.save()
		if command=="sock":
			print(communication.sendaddress,communication.sendsocks)
		if command=="show":
			print("Log index:{},Log record:{},tickets:{}".format(kiosk.log_index,kiosk.log_record,kiosk.cur_tickets))
		if command=="see":
			print("Leader_role{},start_election{},leader_addr{},votes{},known nodes{}"\
			.format(kiosk.leader_role,kiosk.election,kiosk.leader_addr,kiosk.receive_votes,kiosk.known_nodes))
