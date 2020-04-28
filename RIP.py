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
configure_table = []

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
 #CHECK_TIME = 5using to check timeout and garbage collection for routing table

#timers
periodic_timer = None
timeout_timer = None
garbage_collection_timer = None


#when true, there is no need to send trigger update at the same time
is_periodic_send = False

#######################   read configure file         ##########################

def loadConfigFile(fileName):
    """load the configure file and init every thing we need"""
    global my_router_id, input_ports ,output_ports ,configure_table ,listen_pockets 
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
                    configure_table.append(table_item)
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


####################         set timers to response        ##################### 
def initPeriodicTimer():
    """init periodic timer for sending unsolicited response"""
    global periodic_timer
    periodic_timer = threading.Timer(PERIODIC_TIME, sendUnsoclicitedResponse, [])
    periodic_timer.start()
    
    
def initTimeoutTimer():
    global timeout_timer
    timeout_timer = threading.Timer(TIME_OUT, processRouteTimeout, [])
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
            # time out then sign the destination matric 16
            if item['last_update_time'] is None or (time.time()- item['last_update_time']) < TIME_OUT:
                pass
            else:
                print(">>>>>>>>>>>time out, need to update DB") #only to update the metric to 16
                updateRoutingTable(destination, MAX_METRIC, item['next_hop_id'],True)
                
    random_offset = random.randint(-5,5)
    period = TIME_OUT + random_offset
    timeout_timer.cancel()
    timeout_timer = threading.Timer(period, processRouteTimeout, [])
    timeout_timer.start()        


def processGarbageCollection():
    global garbage_collection_timer
    for item in routing_table:
        destination = item['destination']
        if destination != my_router_id:
            #if the garbage time is out  delete it from routing table
            if item['garbage_collect_start'] is None or (time.time() - item['garbage_collect_start']) < GARBAGE_COLLECT_TIME:
                pass
            else:
                print("someone need to be deleted")
                deleteFromTable(destination)
                              
    random_offset = random.randint(-5,5)
    period = GARBAGE_COLLECT_TIME + random_offset
    garbage_collection_timer.cancel()
    garbage_collection_timer = threading.Timer(period, processGarbageCollection, [])
    garbage_collection_timer.start()     



#################################  create the response packet###############
def createPacket( isUpdateOnly):
    """use to compose package"""
    global neighbours
    package = {}  
    package['header'] =  createPacketHeader()
    body = []
    for item in routing_table:
        if isUpdateOnly:
            if item['router_change_flag'] == 'False':
                continue
                
        #poisoned reverse if the next_ho_id = neighbour_id and the destination
        # need throuh neighbour so sign the metric 16
        if str(item['next_hop_id']) in neighbours and item['destination'] != item['next_hop_id']:
            entry = createPacketEntry(item['destination'], 16)
        else:
            entry = createPacketEntry(item['destination'], item['metric'])    
        body.append(entry)
    package['entry'] = body
    return package           

def createPacketHeader():
    """create packet header header format: command|version|must be zero|id"""
    header = [HEAD_ERCOMMAND,HEAD_VERSION,MUST_BE_ZERO,int(my_router_id)]
    return header

def createPacketEntry(destination,metric):
    """create packet entry, format: address family identifier|must be zero| IPv4 address
    |must be zero|must be zero|metric"""  
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
            outSocket.close()
                        
        #once packet has been send the flags should be set into no change
        for item in routing_table:
            item['router_change_flag'] = False
        if isUpdateOnly:
            print("send trigger message to neighbour succeed")
        else:
            print("send unsolicited message to neighbour succeed")   
            
            
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
    #get the line which can get the metric from sender to this router
    senderInfo = getItemFromRoutingTable(sendRouterId)  
      # if exit index >= 0
    #print(">>>>>>>>>>>>>>>>>entry=", entry)
    if senderInfo is None:
        senderInfo = getItemFromConfigerTable(sendRouterId)
        addToRoutingTable(sendRouterId,senderInfo['metric'], "-")
        
    
    for item in entry:
        #print(">>>>>>>>>>>>>>each entry=", item)
        destination = item[2]
        metric = item[5]
        if destination == my_router_id:
            continue
        totalMetric = metric + senderInfo['metric']
        if totalMetric >= MAX_METRIC:
            totalMetric = MAX_METRIC            
        #check the new destination is in the table
        original_item = getItemFromRoutingTable(destination) 
             
        #print(">>>>>>>>check destination>>>>>>>>>>>", original_item)
        if  original_item is None: #if not in the table, add it 
            addToRoutingTable(destination,totalMetric, sendRouterId)             
        else:      
            if original_item['next_hop_id'] == '-': # directly connect
                updateRoutingTable(destination,totalMetric,sendRouterId,False)        
                #check the next hop is  the sender
            elif int(original_item['next_hop_id']) == sendRouterId:
                if int(original_item['metric'])!= totalMetric:
                    updateRoutingTable(destination,totalMetric,sendRouterId,True)
                else:
                    updateRoutingTable(destination,totalMetric,sendRouterId,False)
            else: #check the next hop is  the sender
                if int(original_item['metric'])<= totalMetric:
                    updateRoutingTable(destination,original_item['metric'],original_item['next_hop_id'],False)
                else:
                    updateRoutingTable(destination,totalMetric,sendRouterId,True)


################################operate routing table       ###############
def deleteFromTable(destination):
    for item in  routing_table:
        if item['destination'] == destination or item['next_hop_id'] == destination:
            routing_table.remove(item)
    print(">>>>>>>>>>>>>>>>delete one from table")
    printTable()

def getItemFromConfigerTable(routerId):
    table_item = None
    for item in configure_table:
        if item['destination'] == routerId:
            return item
    return None    

def getItemFromRoutingTable(routerId):
    table_item = None
    for item in routing_table:
        if item['destination'] == routerId:
            return item
    return None


def addToRoutingTable(destination, metric, nextHop):
    table_item = {
                    "destination": destination,
                    "metric": metric, 
                    "next_hop_id": nextHop,
                    "router_change_flag" : True,
                    "garbage_collect_start": None,
                    "last_update_time": time.time()
                }   
    routing_table.append(table_item)
    print(">>>>>>>>>>>>>>>>add to routing table")
    printTable()

def getIndexFromTable(destination):
    for i in range(0, len(routing_table)):
        if routing_table[i]['destination'] ==  destination:
            return i
    return -1


def updateRoutingTable(destination, metric, sender, routeChange):
    """update the neighborhood table""" 
    if metric < 16:
        table_item = {
                        "destination": destination,
                        "metric": metric, 
                        "next_hop_id": sender,
                        "router_change_flag" : routeChange,
                        "garbage_collect_start": None,
                        "last_update_time": time.time()
                    }
        index = getIndexFromTable(destination)
        routing_table[index] = table_item
    else:
        if routeChange:
            table_item = {
                            "destination": destination,
                            "metric": metric, 
                            "next_hop_id": sender,
                            "router_change_flag" : routeChange,
                            "garbage_collect_start": time.time(),
                            "last_update_time": None
                        }
            index = getIndexFromTable(destination)
            routing_table[index] = table_item
            if is_periodic_send:
                pass
            else:
                sendPacket(True) #send the updated route only
    print(">>>>>>>>>>>>>>>>update routing table metric = ", metric)
    printTable()        

########################print the whole routing table #######################      
def printTable():
    """print the RIP routing table"""
    
    global my_router_id
      
    print("+--------------------------------------------------------------+")
    print("|Destination|Metric|Next Hop Id|Route Change|Timeout|Garbage|")
    print("+--------------------------------------------------------------+")

    content_format = "|{0:^11}|{1:^6}|{2:^11}|{3:^12}|{4:^7}|{5:^7}|"
    for item in routing_table:      
        if item['destination'] != my_router_id:
            if(item['last_update_time'] is None):
                timeout = '-'
            else:
                timeout = int(time.time()-item['last_update_time'])
            
            if(item['garbage_collect_start'] is None):
                garbage = '-'
            else:
                garbage = int(time.time()-item['garbage_collect_start'])
            
            if(item['router_change_flag'] is None):
                router_change = '-'
            else:
                router_change = item['router_change_flag']
            print(content_format.format(item['destination'], item['metric'], 
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