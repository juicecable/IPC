#Copyright (c) 2020 Derek Frombach
#IPC Client
"""Proto Dessription:
0x00 is 'Send Package' Request
0x01 is 'Send Package' Acknoledgment
0x02 is Valid Header Recieved
0x03 is Possible Desync
0x04 is Acknoledge Desync
0x05 is Done Recieving
"""

#Imports
import socket #Communications Module
import json #Variable Share Module
import time #Simple Delay

#Globals
ip="localhost" #IPC
port=12645 #Unique Port 1025-65535
buff=1350 #1350 for Internet, 3950-65400 or 1350 for IPC
globs=[] #For Timing Error Recovery
blobs={} #For Data Pooling
sblobs={} #For Data Output Pooling

#Useful Socket Constants
ste=socket.timeout #Socket Timeout Error
se=socket.error #General Socket Error
rdwr=socket.SHUT_RDWR #Graceful Shutdown

#Initalisation of TCP Socket
s=socket.socket(socket.AF_INET, socket.SOCK_STREAM) #TCP/IP Socket
s.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1) #Zero-Latency TCP

#Where Connection Loop would Begin
while True:
    try: s.connect((ip,port)) #Connect
    except: time.sleep(0.1)
    else: break

#Useful Connection Functions
st=s.settimeout #Sets Timeout of Recieve Function in Seconds, None is Wait Forever
ss=s.sendall #Sends All Bytes Immediately in Multiple Packets
sr=s.recv #Recieves TCP Packet, or Fragmented Packet upto buff Bytes, Keeps Leftover Data in Background Buffer to be Read Next Time
sh=s.shutdown #Shuts Down an Active Connection, use RDWR
sc=s.close #Deletes the Connection


#Functions

#Can Recieve Between 1 Byte and 16 Petabytes of Data
def recvPackage(name=b'Default',new=False,enforce=True,ss=ss,sr=sr): #For Recieving Data, name is Bytes, new is if You Require Brand New Data, enforce is if You Actually Care about the Name
    if name in blobs: #Cache Checking
        if new: q=blobs.pop(name)
        else: return name, blobs.pop(name)
    gla=globs.append
    ib=int.from_bytes
    while True: #Garbage Data Flush Loop
        data=sr(buff)
        if data==b'\x00': break
        gla(data)
    i=0
    while i<=1: #Desync Resync Attempt Loop
        ss(b'\x01')
        data=sr(buff) #Header
        """Header Format:
        0x00-0xFF is Name Size
        0x00-0xFF is Data Size #1
        0x00-0xFF is Data Size #2
        0x00-0xFF is Data Size #3
        0x00-0xFF is Data Size #4
        1-256 of 0x00-0xFF is Name
        """
        db=b''
        ns=data[0]+1
        l=ib(data[1:5],'little')+1
        rname=data[5:5+ns]
        if rname==name:
            ss(b'\x02')
            break
        elif i==0 and enforce:
            ss('\x03')
            while True:
                data=sr(buff)
                if data==b'\x04':
                    ss(name)
                    break
        else:
            ss(b'\x02')
            break
        i+=1
    #Now Onto Recieving Data
    while l>0:
        data=sr(buff)
        l-=len(data)
        db+=data
    if rname!=name:
        blobs[rname]=db
    ss(b'\x05')
    return rname, db

#Can Send Between 1 Byte and 16 Petabytes of Data
def sendPackage(data,name=b'Default',new=False,allowPolling=False,ss=ss,sr=sr): #For Sending Data as bytes, name is Bytes, new is if You Require Realtime Data Regardless of Sync, allowPolling is if you want the data to poll (currently unsupported)
    ss(b'\x00')
    gla=globs.append
    while True: #Garbage Data Flush Loop
        rdata=sr(buff)
        if rdata==b'\x01': break
        gla(rdata)
    cname=name
    cdata=data
    while True: #Garbage Data Flush Loop
        ns=bytes([len(cname)-1])
        l=(len(cdata)-1).to_bytes(4,'little')
        ss(ns+l+name)
        rdata=sr(buff)
        if rdata==b'\x02': break
        elif rdata==b'\x03':
            ss('\x04')
            nname=sr(buff)
            if new:
                continue
            elif allowPolling:
                if nname in sblobs:
                    cname=nname
                    cdata=sblobs.pop(nname)
                else:
                    #Do Whatever you need to do to change cname and cdata using polling
                    pass
                sblobs[name]=data
            else:
                if nname in sblobs:
                    cname=nname
                    cdata=sblobs.pop(nname)
    #Now Sending Data
    ss(cdata)
    while True: #Garbage Data Flush Loop
        rdata=sr(buff)
        if rdata==b'\x05': break


#NOW THE ACTUAL CODE
print('Client')
#Test Sending The Fibbonaci Sequence as a List
def Fib(n):
    a=0
    b=1
    if n<0: pass
    elif n==0: return a
    elif n==1: return b
    else:
        for i in range(2,n):
            c=a+b
            a=b
            b=c
        return b

fiblist=[Fib(n) for n in range(0,12)]
data=(json.dumps(fiblist)).encode('utf-8')
sendPackage(data,b'Fib1')
print(fiblist)
#Now Testing Pi Stuff
print('')
def Pi():
    q,r,t,k,m,x=1,0,1,1,3,3
    for j in range(0,1000):
        if 4*q+r-t<m*t:
            yield m
            q,r,t,k,m,x=10*q,10*(r-m*t),t,k,(10*(3*q+r))//t-10*m,x
        else:
            q,r,t,k,m,x=q*k,(2*q+r)*x,t*x,k+1,(q*(7*k+2)+r*x)//(t*x),x+2

pistring=''.join([str(i) for i in Pi()])
pistring=pistring[:1]+'.'+pistring[1:]
data=pistring.encode('utf-8')
sendPackage(data,b'Pi')
print(pistring)
#Now Testing Reverse Direction
print('')
name,data=recvPackage(b'Fib2')
fiblist=json.loads(data.decode('utf-8'))
print(fiblist)
input('Wait for User')

#Now Shutting Down the Connection
sc()
