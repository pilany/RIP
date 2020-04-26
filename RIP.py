import sys
import socket
import select
import json
import time
import threading
import random


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
HEAD_VERSION = 2
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


#when true, there is no need to send trigger update at the same time
is_periodic_send = False

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
                        "destination": int(ports[1]),
                        "metric": int(ports[2]), 
                        "next_hop_id": int(ports[1]),
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
    file.close()
    print('log file succeed')
    print('inports number are {0}'.format(input_ports)) 
    print('outports number are {0}'.format(output_ports))
    print('directly neighbours are {0}'.format(output_ports))
    print('>>>>>>>>>>>>RIP routing table:' + str(my_router_id)) 
    printTable()      
    
    

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
    global listen_sockets
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
    
    
def initTimeoutTimer():
    global timeout_timer
    timeout_timer = threading.Timer(CHECK_TIME, processRouteTimeout, [])
    timeout_timer.start()
    
def initGarbageCollectionTimer():
    global garbage_collection_timer
    garbage_collection_timer = threading.Timer(GARBAGE_COLLECT_TIME, processGarbageCollection, [])
    garbage_collection_timer.start()


def sendUnsoclicitedResponse():
    """send unsoclicited response"""
    global is_periodic_send, periodic_timer
    is_periodic_send = True  #start periodic sending
    sendPacket(False)  #send out the whole routing table
    is_periodic_send = False # end periodic sending
    random_offset = random.randint(-5,5)
    period = PERIODIC_TIME + random_offset
    periodic_timer.cancel()
    periodic_timer = threading.Timer(period, sendUnsoclicitedResponse, [])
    periodic_timer.start()


def processRouteTimeout():
    global timeout_timer
    for item in routing_table:
        destination = item['destination']
        if destination != my_router_id:
            #
            if item['last_update_time'] is None or (time.time()- item['last_update_time']) < TIME_OUT:
                pass
            else:
                next_hop_id = item['next_hop_id']
                updataRoutingTable(destinatin, MAX_METRIC, next_hop_id,true)
                
    random_offset = random.randint(-5,5)
    period = CHECK_TIME + random_offset
    timeout_timer.cancel()
    timeout_timer = threading.Timer(period, processRouteTimeout, [])
    timeout_timer.start()        


def processGarbageCollection():
    global garbage_collection_timer
    for item in routing_table:
        destination = item['destination']
        if destination != my_router_id:
            #
            if item['garbage_collect_start'] is None or (time.time() - item['garbage_collect_start']) < GARBAGE_COLLECT_TIME:
                pass
            else:
                deleteFromTable(destination)
                
                
    random_offset = random.randint(-5,5)
    period = CHECK_TIME + random_offset
    garbage_collection_timer.cancel()
    garbage_collection_timer = threading.Timer(period, processGarbageCollection, [])
    garbage_collection_timer.start()     


def deleteFromTable(destination):
    index = 0
    for item in  routing_table:
        index += 1
        if item['destination'] == destination:
            break
    routing_table.pop(index -1)
    


    
#################################  create the response packet###############
def createPacket( isUpdateOnly):
    """use to compose package"""
    global neighbours
    package = {}  
    package['header'] =  createPacketHeader()
    body = []
    for item in routing_table:
        if isUpdateOnly:
            if item['route_change_flag'] == 'False':
                continue
                
        #poisoned reverse if the next_ho_id == neighbour_id and the destination
        # need throuh neighbour so sign the metric 16
        if str(item['next_hop_id']) in neighbours and item['destination'] != item['next_hop_id']:
            entry = createPacketEntry(item['destination'], 16)
        else:
            entry = createPacketEntry(item['destination'], item['metric'])    
        body.append(entry)
    package['entry'] = body
    return package           

def createPacketHeader():
    """create packet header"""
    header = [HEAD_ERCOMMAND,HEAD_VERSION,MUST_BE_ZERO,int(my_router_id)]
    return header

def createPacketEntry(destination,metric):
    """create packet entry"""
    MUST_BE_ZERO = 0
    ADDRESS_FAMILY_IDENTIFIER = 2    
    entry = [ADDRESS_FAMILY_IDENTIFIER,MUST_BE_ZERO,destination,
             MUST_BE_ZERO,MUST_BE_ZERO,metric]
    return entry
    
    
    

#######################send RIP response ############################
def sendPacket(isUpdateOnly):
    """send out unsolicited response to each neighbour router"""
    try:
        packet = createPacket(isUpdateOnly)
        message = json.dumps(packet).encode('utf-8')
        for port in output_ports:
            outSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            outSocket.sendto(message,('', int(port)))
            print("send message to {} succeed: {}".format(port,message))
            outSocket.close()
        time.sleep(30) 
    except Exception as err:
        print('sendpackage error:{0}'.format(err))
        
        
        
    

        
############################### receive packets from sockets ###########        
def recvPacket():
    '''after the listenSocket the recv threads is receiving data from the socket 
    which connect this socket''' 
    while True:
        rs, ws, es = select.select(listen_sockets,[],[])
        for r in rs:
            if r in listen_sockets:
                message, address = r.recvfrom(2048)
                packet = json.loads(message.decode('utf-8'))
                print("message received: {0}".format(packet))
                if IsValidPacket(packet): #check the packet is or not legal  
                    processPacket(packet)
                else:
                    print("Invalid packet.")
                
 
def IsValidPacket(packet):
    """vertify  validity check the version match 2
    and the routerid and ports are valubable"""
    MAX_METRIC = 16
    HEAD_ERCOMMAND = 2
    HEAD_ERVERSION = 2
    MUST_BE_ZERO = 0    
    isValid = True
    tempRouterid = packet['header'][3]
    if packet['header'][0] != HEAD_ERCOMMAND or packet['header'][1] != HEAD_VERSION :
        isValid =False
    if packet['header'][2] != MUST_BE_ZERO or isValidId(tempRouterid)==False:
        isValid =False
    entry = packet['entry']
    for item in entry:
        if isValidId(item[2])==False or ( item[5]>16 or item[5] <0):
            isValid =False
    return isValid
 
########################process       packet          #######################
#deal with packet 
def processPacket(packet):
    sendRouterId = packet['header'][3]
    entry = packet['entry']
    
    senderInfo = getItemFromTable(sendRouterId)
    table_item = senderInfo[0]
    index = senderInfo[1]-1
    for item in entry:
        destination = item[2]
        metric = item[5]
        
        totalMetric = metric + table_item['metric']
        print(metric, table_item['metric'])
        if totalMetric > 16:
            totalMetric = 16
        if senderInfo[0] == None:#if it doesnot in the routing table, add to table
            if totalMetric < 16:
                addToRoutingTable(destination, totalMetric, sendRouterId)
        else:
            
            if table_item['next_hop_id'] == sendRouterId:
                if int(table_item['metric'] )!= totalMetric:
                    updateRoutingTable(index, destination,totalMetric,sendRouterId,True)
                else:
                    updateRoutingTable(index, destination,totalMetric,sendRouterId,False)
            else:
                if int(table_item['metric'] )< totalMetric:
                    pass
                else:
                    updateRoutingTable(index, destination,totalMetric,sendRouterId,True)
            
        
def getItemFromTable(routerId):
    table_item = None
    index = 0
    for item in routing_table:
        index += 1
        if item['destination'] == routerId:
            table_item = item
    return [table_item, index]


def addToRoutingTable(destination, metric, nextHop):
    table_item = {
                    "destination": destination,
                    "metric": metric, 
                    "next_hop_id": nextHop,
                    "router_change_flag" : True,
                    "garbage_collect_start": None,
                    "last_update_time": None
                }   
    routing_table.append(table_item)
    print(">>>>>>>>>>>>>>>>add to routing table")
    printTable()


def updateRoutingTable(index,destination, metric, sender, routeChange = False):
    """uodate the neighborhood table""" 
    print( "index = ", index)
    if metric < 16:
        table_item = {
                        "destination": destination,
                        "metric": metric, 
                        "next_hop_id": sender,
                        "router_change_flag" : routeChange,
                        "garbage_collect_start": None,
                        "last_update_time": None
                    }
        routing_table[index] = table_item
    else:
        if routeChange:
            table_item = {
                            "destination": destination,
                            "metric": metric, 
                            "next_hop_id": sender,
                            "router_change_flag" : routeChange,
                            "garbage_collect_start": None,
                            "last_update_time": None
                        }
            routing_table.append(table_item)
            if is_periodic_send:
                pass
            else:
                sendPacket(True) #send the updated route only
    print(">>>>>>>>>>>>>>>>update routing table")
    printTable()        

########################print the whole routing table #######################      
def printTable():
    """print the RIP routing table"""
    
    global my_router_id
      
    print('-'* 90)
    mat = "{:12}\t{:12}\t{:12}\t{:12}\t{:12}\t{:12}"
    print(mat.format("Destination","Metric","Next Hop","Flag","Garbage","Time Out"))
    for item in routing_table:      
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
                             item['next_hop_id'],router_change,garbage,timeout))
        


def main():
    """main entrance"""
    fileName = sys.argv[1]
    #start read configure file
    loadConfigFile(fileName)
    
    initListenSocket()#start listenthreads
    initPeriodicTimer()#init the periodic timer
    initTimeoutTimer()#init timeout timer
    initGarbageCollectionTimer()#init garbage collection timer
    
    
    recvPacket() #start recvThreads   

main()