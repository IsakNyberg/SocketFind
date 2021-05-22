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


def flood(connections, bytes_to_send):
    for address in connections:
        UDPServerSocket.sendto(bytes_to_send, address)


def game_thread(field, connections):
    tick = 0
    clock = pygame.time.Clock()
    while 1:
        field.tick()
        tick += 1
        clock.tick(128)
        if tick % 8 == 0:
            flood(connections, field.to_bytes())


if __name__ == '__main__':
    connections = []
    field = Field()
    thread = Thread(target=game_thread, args=(field, connections, ))
    thread.start()
    while len(connections) < 255:
        bytesAddressPair = UDPServerSocket.recvfrom(bufferSize)
        message = bytesAddressPair[0]
        address = bytesAddressPair[1]

        if address not in connections:
            connections.append(address)
            field.new_player()
            index = len(connections) - 1
        else:
            index = connections.index(address)

        if message == b'0x00':
            UDPServerSocket.sendto(index.to_bytes(1, byteorder='big'), address)

        field.steer(index, message[0] - 1, message[1] - 1)
        flood(connections, field.to_bytes())
        # clientMsg = "Message from Client:{}".format(message)
        # clientIP = "Client IP Address:{}".format(address)
        # print(clientMsg)
        # print(clientIP)
