import sys
import socket
import select
import json
import time


#information from configure file
my_router_id = None
input_ports =[]
output_ports = []
neighbours = []
listen_sockets = []

#routing table
routing_table = []

#routing table config data
MAX_METRIC = 16
HEAD_ERCOMMAND = 2
HEAD_ERVERSION = 2
MUST_BE_ZERO = 0
ADDRESS_FAMILY_IDENTIFIER = 2

#default timer setting
TIME_OUT = 50 #default 180
GARBAGE_COLLECT_TIME = 30 #default 120
PERIODIC_TIME = 10 #default 30
CHECK_TIME = 4 #using to check timeout and garbage collection for routing table

#timers
periodic_timer = None
timeout_timer = None
garbage_collection_timer = None


#######################   read configure file         ##########################

def loadConfigFile(fileName):
    """load the configure file and init every thing we need"""
    global my_router_id, input_ports ,output_ports ,routing_table ,listen_pockets 
    file = open(fileName)
    lines = file.read().splitlines()
    for line in lines:
        data = line.split(' ')
        if data[0] == 'router-id':
            if isValidId(int(data[1])):
                my_router_id = int(data[1])
            else:
                print('Invalid Id Number')
                exit(0)
        elif data[0] == 'input-ports':
            ports = data[1].split(',')
            for port in ports:
                if isValidPort(int(port)):
                    input_ports.append(int(port))
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
                        "next_hop_id": my_router_id,
                        "router_change_flag" : False,
                        "garbage_collect_start": None,
                        "last_update_time": None
                    }
                    routing_table.append(table_item)
                    output_ports.append(ports[0])
                    neighbours.append(ports[1])
                else:
                    print('Invalid Id Number or RouterId in outputs')
                    exit(0)                    
        else:         
            print('Invalid configure file')
            exit(0)             
    print('log file succeed')
    print('routerId = {}'.format(my_router_Id))
    print('inports number are {0}'.format(input_ports)) 
    print('outports number are {0}'.format(output_ports))
    print('directly neighbours are {0}'.format(output_ports))
    printTable()      
    file.close()
    return my_router_id

#check the port is or not between 1024 and 64000
def isValidPort(port):
    if port >=1024 and port <=64000:
        return True
    else:
        return False
#check the router Id is or not between 1 and 64000
def isValidId(num):
    if num>=1 and num <= 64000:
        return True
    else:
        return False


##################### create listen sockets to each neighbor###################   
def initListenSocket():
    """init all the ports which needs to  be listen"""
    try:
        for port in input_ports:
            inSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            inSocket.bind(('', int(port)))
            listen_sockets.append(inSocket)
            print('creat listen socket:{} succeed'.format(port))
    except Exception as err:
        print('creat listen socket error:{0}'.format(err))


####################         set three timers             ##################### 
def initPeriodicTimer():
    """init periodic timer for sending unsolicited response"""
    global periodic_timer
    periodic_timer = threading.Timer(PERIODIC_TIME, sendUnsoclicitedResponse, [])
    periodic_timer.start()
    
    
def    initTimeoutTimer():
    global timeout_timer
    timeout_timer = threading.Timer(CHECK_TIME, processRouteTimeout, [])
    timeout_timer.start()
    
def    initGarbageCollectionTimer():
    global garbage_collection_timer
    garbage_collection_timer = threading.Timer(GARBAGE_COLLECT_TIME, processGarbageCollection, [])
    garbage_collection_timer.start()






def updateRoutingTable(packet):
    """uodate the neighborhood table"""
    
#################################  create the response packet###############
def createPackage(routerId, isUpdateOnly):
    """use to compose package"""
    global neighbours
    package = {}  
    package['header'] =  createHeader(routerId)
    body = []
    for table_item in routing_table:
        if isUpdateOnly:
            if table['route_change_flag'] == 'False':
                continue
                
        #poisoned reverse if the next_ho_id == neighbour_id and the destination
        # need throuh neighbour so sign the metric 16
        if str(table['next_hop_id'] in neighbours 
                and table['destination'] != table['next_hop_id']):
            entry = createPacketEntry(table['destination'], 16)
        else:
            entry = createPacketEntry(table['destination'], table['metric'])    
        body.append(entry)
    package['body'] = body
    return package           

def createPacketHeader():
    """create packet header"""
    header = [HEAD_ERCOMMAND,HEAD_ERVERSION,MUST_BE_ZERO,int(routerId)]
    return header

def createPacketEntry(destination,metric):
    """create packet entry"""
    MUST_BE_ZERO = 0
    ADDRESS_FAMILY_IDENTIFIER = 2    
    entry = [ADDRESS_FAMILY_IDENTIFIER,MUST_BE_ZERO,destination,
             MUST_BE_ZERO,MUST_BE_ZERO,metric]
    return entry
    
    
    

    
def sendData(message):
    """send Data, as we need notice all the neighbers"""
    try:
        
        for port in output_ports:
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
                

        
def printTable():
    """print the RIP routing table"""
    
    global router_id
    print('>>>>>>>>>>>>RIP routing table:' + str(my_router_id))    
    print('-'* 90)
    mat = "{:12}\t{:12}\t{:12}\t{:12}\t{:12}\t{:12}"
    print(mat.format("Destination","Metric","Next Hop","Flag","Garbage","Time Out"))
    for item in routingtable:      
        if item['destination'] != my_router_id:
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
        


def main():
    """main entrance"""
    fileName = sys.argv[1]
    #start read configure file
    routerId=loadConfigFile(fileName)
    
    initListenSocket()#start listenthreads
    initPeriodicTimer()#init the periodic timer
    initTimeoutTimer()#init timeout timer
    initGarbageCollectionTimer()#init garbage collection timer
    
    while True:
        sendData(json.dumps(constructPackage(routerId)).encode('utf-8'))
        recvData() #start recvThreads   
    releaseSocket()
main()