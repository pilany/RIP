import sys
import socket

routerId = 0
inputPorts =[]
outputPorts = []
neighberhood = {}
listenSockets = []

def startPacking():
    """use to compose package"""
    


def sendData(message):
    """send Data, as we need notice all the neighbers"""
    for port in outports:
        outSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        outSocket.sendto(message,('', port))


def recvData():
    '''after the listenSocket the recv threads is receiving data from the socket 
    which connect this socket'''
    while True:
        rs, ws, es = select.select(listenSockets,[],[])
        for r in rs:
            if r in listenSockets:
                package, address = r.recvfrom(2048)
                message = package.encode('utf-8')
                print("message received: {0}".format(message))

def initListenSocket():
    """init all the ports which need to listen"""
    for port in inputPorts:
        inSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        inSocket.bind('', port)
        listenSockets.append(inSocket)
        
        
def printTable():
    """print the RIP routing table"""
    print('RIP routing table:')    
    print('-'* 90)
    mat = "{:20}\t{:20}\t{:20}\t{:20}"
    print(mat.format("Destination","Next Hop","Metric","Tag"))
    for key in neighberhood:
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
                if (isValidPort(int(ports[0])) and isValidId(int(ports[1])) and int(ports[1]) != routerId):
                    neighberhood[ports[1]] = [ports[1],ports[2],0]
                    outputPorts.append(ports[0])
                else:
                    print('Invalid Id Number in outputs')
                    exit(0)                    
        else:         
            print('Invalid configure file')
            exit(0)             
    print('log file succeed')
    print('routerId = {}'.format(routerId))
    print('inports number is {0}'.format(inputPorts))    
    printTable()
       
    file.close()

def main():
    """main entrance"""
    "fileName = sys.argv[1]"
    fileName = "router1.conf"
    loadConfig(fileName)
    

main()