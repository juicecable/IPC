#Copyright (c) 2020 Derek Frombach
#IPC SERVER
"""Proto Description:
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
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #Unbind when Done
s.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1) #Zero-Latency TCP

#Initalisation of Server
s.bind((ip, port)) #Starting Server
s.listen(1) #Listen for Connections

#Useful Socket Functions
sc=socket.close #Stops Listening, Unbinds the Server and Deletes the Socket

#Where Connection Loop would Begin
conn, addr=s.accept() #Accept Connection

#Useful Connection Functions
ct=conn.settimeout #Sets Timeout of Recieve Function in Seconds, None is Wait Forever
cs=conn.sendall #Sends All Bytes Immediately in Multiple Packets
cr=conn.recv #Recieves TCP Packet, or Fragmented Packet upto buff Bytes, Keeps Leftover Data in Background Buffer to be Read Next Time
ch=conn.shutdown #Shuts Down an Active Connection, use RDWR
cc=conn.close #Deletes the Connection


#Functions

#Can Recieve Between 1 Byte and 16 Petabytes of Data
def recvPackage(name=b'Default',new=False,enforce=True,cs=cs,cr=cr): #For Recieving Data, name is Bytes, new is if You Require Brand New Data, enforce is if You Actually Care about the Name
    if name in blobs: #Cache Checking
        if new: q=blobs.pop(name)
        else: return name, blobs.pop(name)
    gla=globs.append
    ib=int.from_bytes
    while True: #Garbage Data Flush Loop
        data=cr(buff)
        if data==b'\x00': break
        gla(data)
    i=0
    while i<=1: #Desync Resync Attempt Loop
        cs(b'\x01')
        data=cr(buff) #Header
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
            cs(b'\x02')
            break
        elif i==0 and enforce:
            cs('\x03')
            while True:
                data=cr(buff)
                if data==b'\x04':
                    cs(name)
                    break
        else:
            cs(b'\x02')
            break
        i+=1
    #Now Onto Recieving Data
    while l>0:
        data=cr(buff)
        l-=len(data)
        db+=data
    if rname!=name:
        blobs[rname]=db
    cs(b'\x05')
    return rname, db

#Can Send Between 1 Byte and 16 Petabytes of Data
def sendPackage(data,name=b'Default',new=False,allowPolling=False,cs=cs,cr=cr): #For Sending Data as bytes, name is Bytes, new is if You Require Realtime Data Regardless of Sync, allowPolling is if you want the data to poll (currently unsupported)
    cs(b'\x00')
    gla=globs.append
    while True: #Garbage Data Flush Loop
        rdata=cr(buff)
        if rdata==b'\x01': break
        gla(rdata)
    cname=name
    cdata=data
    while True: #Garbage Data Flush Loop
        ns=bytes([len(cname)-1])
        l=(len(cdata)-1).to_bytes(4,'little')
        cs(ns+l+name)
        rdata=cr(buff)
        if rdata==b'\x02': break
        elif rdata==b'\x03':
            cs('\x04')
            nname=cr(buff)
            if new: continue
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
    cs(cdata)
    while True: #Garbage Data Flush Loop
        rdata=cr(buff)
        if rdata==b'\x05': break


#NOW THE ACTUAL CODE
print('Server')
#Test recieving the Fibbonaci Sequence
name,data=recvPackage(b'Fib1')
fiblist=json.loads(data.decode('utf-8'))
print(fiblist)
#Now Testing Recieiving Pi
print('')
name,data=recvPackage(b'Pi')
pistring=data.decode('utf-8')
print(pistring)
#Now Testing Reverse Direciton
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
fiblist=[Fib(n) for n in range(12,20)]
print(fiblist)
data=(json.dumps(fiblist)).encode('utf-8')
sendPackage(data,b'Fib2')
input('Wait for User')

#Now Shutting Down the Connection
ch(rdwr)
sc()
