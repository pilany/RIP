import sys
import socket
import select
import json
import time



inputPorts =[]
outputPorts = []
neighberhood = {}
listenSockets = []



def constructPackage(routerId):
    """use to compose package"""
    package = {}
    package['header'] = [2,int(routerId)] #header: version, router_id
    body = []
    for key in neighberhood.keys():#body: [destination, metrics]
        body.append([key,neighberhood[key][1]])
    package['body'] = body
    return package           

def sendData(message):
    """send Data, as we need notice all the neighbers"""
    try:
        
        for port in outputPorts:
            outSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            outSocket.sendto(message,('', int(port)))
            print("send message to {} succeed: {}".format(port,message))
            outSocket.close()
        time.sleep(30) 
    except Exception as err:
        print('sendpackage error:{0}'.format(err))
    
def IsValidPacket(packet):
    """vertify  validity """
    isValid = True
    tempRouterid = int(packet['header'][1])
    if(packet['header'][0] != 2 or isValidId(tempRouterid)== False):
        isValid =False
    return isValid
        
        
def recvData():
    '''after the listenSocket the recv threads is receiving data from the socket 
    which connect this socket''' 
    
    rs, ws, es = select.select(listenSockets,[],[])
    for r in rs:
        if r in listenSockets:
            package, address = r.recvfrom(2048)
            message = json.loads(package.decode('utf-8'))
            print("message received: {0}".format(message))
                
                
def releaseSocket():
    for sock in inSocket:
        sock.close()
    

def initListenSocket():
    """init all the ports which need to listen"""
    try:
        for port in inputPorts:
            inSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            inSocket.bind(('', int(port)))
            listenSockets.append(inSocket)
            print('creat listen socket:{} succeed'.format(port))
    except Exception as err:
        print('creat listen socket error:{0}'.format(err))
        
        
def printTable():
    """print the RIP routing table"""
    print('RIP routing table:')    
    print('-'* 90)
    mat = "{:20}\t{:20}\t{:20}\t{:20}"
    print(mat.format("Destination","Next Hop","Metric","Tag"))
    for key in neighberhood.keys():
        datas = neighberhood[key]
        print(mat.format(key, str(datas[0]),str(datas[1]),str(datas[2])))
        

def isValidPort(port):
    if port >=1024 and port <=64000:
        return True
    else:
        return False

def isValidId(num):
    if num>=1 and num <= 64000:
        return True
    else:
        return False
    
def loadConfig(fileName):
    """load the configure file and init every thing we need"""
    file = open(fileName)
    lines = file.read().splitlines()
    for line in lines:
        data = line.split(' ')
        if data[0] == 'router-id':
            if isValidId(int(data[1])):
                routerId = data[1]
            else:
                print('Invalid Id Number')
                exit(0)
        elif data[0] == 'input-ports':
            ports = data[1].split(',')
            for port in ports:
                if isValidPort(int(port)):
                    inputPorts.append(port)
                else:
                    print('Invalid Id Number in input-ports')
                    exit(0)
        elif data[0] == 'outputs':
            items = data[1].split(',')
            for item in items:
                ports = item.split('-')
                if (isValidPort(int(ports[0])) and isValidId(int(ports[1])) and ports[1] != routerId):
                    neighberhood[ports[1]] = [ports[1],ports[2],0]
                    outputPorts.append(ports[0])
                else:
                    print('Invalid Id Number or RouterId in outputs')
                    exit(0)                    
        else:         
            print('Invalid configure file')
            exit(0)             
    print('log file succeed')
    print('routerId = {}'.format(routerId))
    print('inports number is {0}'.format(inputPorts)) 
    print('outports number is {0}'.format(outputPorts))
    printTable()      
    file.close()
    return routerId

def main():
    """main entrance"""
    fileName = sys.argv[1]
    #fileName = "router1.conf"
    routerId=loadConfig(fileName)
    initListenSocket()#start listenthreads
     
    
    while True:
        sendData(json.dumps(constructPackage(routerId)).encode('utf-8'))
        recvData() #start recvThreads   
    releaseSocket()
main()