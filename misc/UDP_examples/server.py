import time
import random
import socket

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind(('',48000))

while True:
    time.sleep(0.1)

    message, address = server_socket.recvfrom(1024)

    print(message.decode('utf-8'),address)
    # server_socket.sendto(b'forever',address)



