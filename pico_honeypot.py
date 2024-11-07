import network
import socket
import time

# Telnet command constants
IAC  = 255  # "Interpret As Command"
DONT = 254
DO   = 253
WONT = 252
WILL = 251
SE   = 240  # Subnegotiation End
NOP  = 241  # No Operation
ECHO = 1    # Echo option

TELNET_PORT = 23
BUFFER_SIZE = 1024

# Fake file system for demonstration purposes
fake_file_system = {
    'home': {
        'user': {
            'file1.txt': 'This is a test file. Content here is for demo purposes.',
            'file2.log': 'Log file sample content.',
        },
        'readme.txt': 'Welcome to the IoT device. This is a fake file system.',
    },
    'etc': {
        'config.cfg': 'Configuration settings go here.',
        'hosts': '127.0.0.1 localhost\n192.168.1.1 router',
    },
    'var': {
        'log': {
            'syslog': 'System log placeholder.',
            'error.log': 'Error log content placeholder.',
        }
    }
}

current_path = ['home']
username = 'admin'
password = 'password'

# Helper function to get the current directory reference
def get_current_directory():
    dir_ref = fake_file_system
    for part in current_path:
        dir_ref = dir_ref.get(part, {})
    return dir_ref

# Function to handle Telnet negotiation
def handle_telnet_negotiation(data):
    i = 0
    output = b''
    while i < len(data):
        if data[i] == IAC:
            # Telnet command sequence
            i += 1
            if i < len(data):
                cmd = data[i]
                if cmd in (DO, DONT, WILL, WONT):
                    i += 1  # Skip the option byte
                elif cmd == SE or cmd == NOP:
                    pass  # No operation needed
                else:
                    pass  # Ignore other commands
        else:
            output += bytes([data[i]])
        i += 1
    return output

# Connect to Wi-Fi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect('INALAN_2.4G_ehTair', 'zJYkqCCs')

print('Connecting to Wi-Fi...')
while not wlan.isconnected():
    time.sleep(1)

print('Connected:', wlan.ifconfig())

# Create and bind a socket to port 23 (Telnet)
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('', TELNET_PORT))
server_socket.listen(1)
print('Honeypot listening on port 23...')

while True:
    conn, addr = server_socket.accept()
    print('Connection from:', addr)
    conn.settimeout(60)  # Set a timeout for socket operations

    try:
        # Send Telnet WILL ECHO to suppress local echo on client
        conn.sendall(bytes([IAC, WILL, ECHO]))

        conn.sendall(b'\r\npico-honeypot\r\n\r\n')
        conn.sendall(b'login: ')

        # Receive and process the username
        user_input = b''
        while not user_input.endswith(b'\n'):
            data = conn.recv(BUFFER_SIZE)
            if not data:
                raise Exception('Connection closed by client.')
            data = handle_telnet_negotiation(data)
            user_input += data
        user_input = user_input.strip().decode('utf-8', 'ignore')

        if not user_input:
            conn.sendall(b'\r\nError: No input received. Connection closed.\r\n')
            conn.close()
            print('Connection closed due to no input')
            continue

        if user_input != username:
            conn.sendall(b'\r\nLogin failed.\r\n')
            conn.close()
            print('Connection closed due to invalid username')
            continue

        conn.sendall(b'password: ')

        # Receive and process the password
        pass_input = b''
        while not pass_input.endswith(b'\n'):
            data = conn.recv(BUFFER_SIZE)
            if not data:
                raise Exception('Connection closed by client.')
            data = handle_telnet_negotiation(data)
            pass_input += data
        pass_input = pass_input.strip().decode('utf-8', 'ignore')

        if not pass_input:
            conn.sendall(b'\r\nError: No input received. Connection closed.\r\n')
            conn.close()
            print('Connection closed due to no input')
            continue

        if pass_input != password:
            conn.sendall(b'\r\nLogin failed.\r\n')
            conn.close()
            print('Connection closed due to invalid password')
            continue

        conn.sendall(b'\r\nLogin successful.\r\n')

        while True:
            conn.sendall(b'> ')
            cmd_input = b''
            while not cmd_input.endswith(b'\n'):
                data = conn.recv(BUFFER_SIZE)
                if not data:
                    raise Exception('Connection closed by client.')
                data = handle_telnet_negotiation(data)
                cmd_input += data
            cmd_input = cmd_input.strip().decode('utf-8', 'ignore')

            if not cmd_input:
                continue  # Empty command, prompt again

            print(f'Debug: Received command: {cmd_input}')
            command_parts = cmd_input.split()
            command = command_parts[0]

            if command == 'ls':
                dir_ref = get_current_directory()
                if isinstance(dir_ref, dict):
                    conn.sendall((', '.join(dir_ref.keys()) + '\n').encode())
                else:
                    conn.sendall(b'Error: Current path is not a directory\n')

            elif command == 'cd':
                if len(command_parts) > 1:
                    target = command_parts[1]
                    dir_ref = get_current_directory()
                    if target == '..':
                        if len(current_path) > 1:
                            current_path.pop()
                    elif target in dir_ref and isinstance(dir_ref[target], dict):
                        current_path.append(target)
                    else:
                        conn.sendall(b'Error: Directory not found\n')
                else:
                    conn.sendall(b'Usage: cd <directory>\n')

            elif command == 'cat':
                if len(command_parts) > 1:
                    file_name = command_parts[1]
                    dir_ref = get_current_directory()
                    if file_name in dir_ref and isinstance(dir_ref[file_name], str):
                        conn.sendall((dir_ref[file_name] + '\n').encode())
                    else:
                        conn.sendall(b'Error: File not found or is a directory\n')
                else:
                    conn.sendall(b'Usage: cat <filename>\n')

            elif command == 'pwd':
                conn.sendall(('/' + '/'.join(current_path) + '\n').encode())

            else:
                conn.sendall(b'Error: Command not recognized\n')

    except Exception as e:
        print(f'Error: {e}')
    finally:
        conn.close()
        print('Connection closed')

