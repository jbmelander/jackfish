import time
import socket

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.makefile('wb')
addr = ('127.0.0.1',13000)

for i in range(1000):
    time.sleep(1)
    message = 'run {}'.format(i)

#     message = bytes(message, 'utf-8')
#     client_socket.sendto(message,addr)

