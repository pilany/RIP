import sys
import socket

routerId = 0
inputPorts =[]
outputPorts = []
neighberhood = {}


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
                if (isValidPort(int(ports[0])) and isValidId(int(ports[1]))):
                    neighberhood[ports[1]] = [ports[1],ports[2]]
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
    print('neighberhood number is {0}'.format(outputPorts))
       
    file.close()

def main():
    """main entrance"""
    "fileName = sys.argv[1]"
    fileName = "router1.conf"
    loadConfig(fileName)
    

main()