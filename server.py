import pygame
import socket
import math
from threading import Thread

from field import *
localIP = ""
localPort = 63834
bufferSize = 1024
msgFromServer = "Hello UDP Client"

bytesToSend = str.encode(msgFromServer)
UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
UDPServerSocket.bind((localIP, localPort))
print("UDP server up and listening")


def flood(connections, connections_ttl, bytes_to_send):
    try:
        for i in range(len(connections)):
            bytes_to_send += i.to_bytes(1, 'big')
            UDPServerSocket.sendto(bytes_to_send, connections[i])
            connections_ttl[i] -= 1
    except IndexError:
        print('Index error in flood')


def game_thread(field, connections, connections_ttl):
    tick = 0
    clock = pygame.time.Clock()
    while 1:
        field.tick()
        tick += 1
        clock.tick(128)
        if tick % 8 == 0:
            flood(connections,connections_ttl,  field.to_bytes())



if __name__ == '__main__':
    connections = []
    connections_ttl = []
    field = Field()
    thread = Thread(target=game_thread, args=(field, connections, connections_ttl, ))
    thread.start()
    while len(connections) < 255:
        bytesAddressPair = UDPServerSocket.recvfrom(bufferSize)
        message = bytesAddressPair[0]
        address = bytesAddressPair[1]

        if address not in connections:
            connections.append(address)
            connections_ttl.append(2000)
            field.new_player()

        index = connections.index(address)
        connections_ttl[index] = 2000
        field.steer(index, message[0] - 1, message[1] - 1)

        for i in range(len(connections_ttl)):
            if connections_ttl[i] < 0:
                del connections_ttl[i]
                del connections[i]
                field.remove(i)
                break
