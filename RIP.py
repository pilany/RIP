import sys
import socket
import select
import json
import time


#my_router_info
router_id = None
inputPorts =[]
outputPorts = []
routingtable = []
listenSockets = []

MAX_METRIC = 16
HEAD_ERCOMMAND = 2
HEAD_ERVERSION = 2

#time control
TIME_OUT = 50 #default 180
GARBAGE_COLLECT_TIME = 30 #default 120
PERIODIC_TIME = 10 #default 30
CHECK_TIME = 5 #using to check timeout and garbage collection for routing table

def updateRoutingTable(packet):
    """uodate the neighborhood table"""
    

def constructPackage(routerId):
    """use to compose package"""
    package = {}
    package['header'] = [2,int(routerId)] #header: version, router_id
    body = []
    for item in routingtable:#body: [destination, metrics]
        body.append([item['destination'],item['metric']])
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
    """vertify  validity check the version match 2
    and the routerid and ports are valubable"""
    isValid = True
    tempRouterid = int(packet['header'][1])
    if(packet['header'][0] != 2 or isValidId(tempRouterid)== False):
        isValid =False
    for i in packet['body']:
        if(isValidId(int( i[0]))==False) or int(i[1]) == 16:
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
            isValid = IsValidPacket(message)  
            if isValis == False:
                print("Invalid packet.")
            else:
                updateTable(message)
                
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
    
    global router_id
    print('>>>>>>>>>>>>RIP routing table:' + str(router_id))    
    print('-'* 90)
    mat = "{:12}\t{:12}\t{:12}\t{:12}\t{:12}\t{:12}"
    print(mat.format("Destination","Metric","Next Hop","Flag","Garbage","Time Out"))
    for item in routingtable:      
        if item['destination'] != router_id:
            if(item['last_update_time'] is None):
                timeout = '-'
            else:
                timeout = int(TIME_OUT - 
                              int(time.time()-item['last_update_time']))
            
            if(item['garbage_collect_start'] is None):
                garbage = '-'
            else:
                garbage = int(GARBAGE_COLLECT_TIME - 
                              int(time.time()-item['garbage_collect_start']))
            
            if(item['router_change_flag'] is None):
                router_change = '-'
            else:
                router_change = item['router_change_flag']
            print(mat.format(item['destination'], item['metric'], 
                             item['next_hop'],router_change,garbage,timeout))
        

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
################################################################################
#              stage 1 : read config file                                      #
################################################################################
def loadConfigFile(fileName):
    """load the configure file and init every thing we need"""
    global router_id, inputPorts ,outputPorts ,routingtable ,listenSockets 
    file = open(fileName)
    lines = file.read().splitlines()
    for line in lines:
        data = line.split(' ')
        if data[0] == 'router-id':
            if isValidId(int(data[1])):
                routerId = int(data[1])
            else:
                print('Invalid Id Number')
                exit(0)
        elif data[0] == 'input-ports':
            ports = data[1].split(',')
            for port in ports:
                if isValidPort(int(port)):
                    inputPorts.append(int(port))
                else:
                    print('Invalid Id Number in input-ports')
                    exit(0)
        elif data[0] == 'outputs':
            items = data[1].split(',')
            for item in items:
                ports = item.split('-')
                if (isValidPort(int(ports[0])) and isValidId(int(ports[1]))):
                    table_item = {
                        "destination": ports[1],
                        "metric": 0, 
                        "next_hop": ports[0],
                        "router_change_flag" : False,
                        "garbage_collect_start": None,
                        "last_update_time": None
                    }
                    routingtable.append(table_item)
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
    routerId=loadConfigFile(fileName)
    initListenSocket()#start listenthreads
     
    
    while True:
        sendData(json.dumps(constructPackage(routerId)).encode('utf-8'))
        recvData() #start recvThreads   
    releaseSocket()
main()