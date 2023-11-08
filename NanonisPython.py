"""
To generalize this need to have a case system (if, elif, elseif, etc.) for each argument type.
Right now writing specifically for Scan.Action

Header
Header size is fixed to 40 bytes (last 2 bytes are currently not used and they should be set to zero) and contains the following elements:
- Command name (string) (32 bytes) is the name of the executed command. It matches one of the function names described in the Functions section of this document (i.e. BiasSpectr.Open). Maximum number of characters is 32.
- Body size (int) (4 bytes) is the size of the message body in bytes.
- Send response back (unsigned int16) (2 bytes) defines if the server sends a message back to the client (=1) or not (=0). All functions can return at least the error information returned after executing the specified function.

*** Written by Amit Finkler, 05.02.2020. I take no responsibility for anything that may happen to your system when using my code. I am like a pianist who does not know how to read notes, but has good musical hearing. ***

Right now all the TCP commands (with socket or sock in them) are commented out. The script is merely for testing purposes and if one want to generalize it one would need to re-write most of it to accommodate for a general input/output. It is mostly for debugging purposes but it serves it well.

"""

import struct
import socket
import bitstring

ip_addr = '10.0.0.37'  # or 'IP address'
port = 6501  # opened for listening by the nanonis program

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((ip_addr, port)) # For this to work the nanonis program needs to be on in the background

msg = b'Scan.Action'  # needs to be in a 'bytes' object
ScanAction = 'start'
ScanDirection = 'up'
SendBack = False

def command_name(msg, scan_action='start', scan_direction='up', send_back=False):
    """    The command consists of the header + body. The header is msg_hex + body_size + send_back + 2 bytes of zeros(0000). The body is the arguments"""
    string = str(len(msg)) + 's'                            # length of string plus a suffix 's': this is used in the format argument of the next function (i.e.'10s' means a single 10-byte string)
    msg_hex = struct.pack('>' + string, msg).hex().upper()  # format msg into big-endian hex of msg
    msg_hex = msg_hex[::-1].zfill(64)[::-1]                 # padding with zeros (zfill) to get to 32 bytes (each hex is two)/[::-1] makes sure to pad to the right.
    print('Command Name in hex is:' + msg_hex)
    
    if scan_action == 'start':
        scan_action = 0
    elif scan_action == 'stop':
        scan_action = 1
    elif scan_action == 'pause':
        scan_action = 2
    else:  # resume
        scan_action = 3
    scan_action = bitstring.BitArray('uint:16=' + str(scan_action)).hex.upper()                             #scan_action in hex

    if scan_direction == 'up':
        scan_direction = 1
    else:
        scan_direction = 0
    scan_direction = bitstring.BitArray('uint:32=' + str(scan_direction)).hex.upper()                       #scan_direction in hex

    body_size = bitstring.BitArray('int:32=' + str(int(len(scan_action + scan_direction)/2))).hex.upper()   #body size in hex

    if not send_back:
        send_back = '0000'
    else:
        send_back = '0001'

    header = msg_hex + body_size + send_back + '0000'
    body = scan_action + scan_direction
    message = header + body
    return message

Message = command_name(msg, ScanAction, ScanDirection, SendBack)  # full message in hex
h = bytearray(int(len(Message)/2))                                # define h as an array with size= number of bytes of the full message

for k in range(int(len(Message)/2)):                              # this loop runs the same number of iterations as bytes of the full message and fills h array
    t = bitstring.BitArray(hex=Message[2*k:2*k+2])
    h[k] = t.uint

print('Full message in hex is:' + Message)
print('h (message in binary) is:')
print(h)

sock.send(h)  
if SendBack:
    reply = sock.recv(1024)
    print(reply)
sock.close()
