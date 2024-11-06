import socket
import threading
import json

# Define message structure class
class ChatMessage:
    def __init__(self):
        self.REPORT_REQUEST_FLAG = 0
        self.REPORT_RESPONSE_FLAG = 0
        self.JOIN_REQUEST_FLAG = 0
        self.JOIN_REJECT_FLAG = 0
        self.JOIN_ACCEPT_FLAG = 0
        self.NEW_USER_FLAG = 0
        self.QUIT_REQUEST_FLAG = 0
        self.QUIT_ACCEPT_FLAG = 0
        self.ATTACHMENT_FLAG = 0
        self.NUMBER = 0
        self.USERNAME = ""
        self.FILENAME = ""
        self.PAYLOAD_LENGTH = 0
        self.PAYLOAD = ""

    def to_dict(self):
        return self.__dict__

    def from_dict(self, message_dict):
        for key, value in message_dict.items():
            setattr(self, key, value)

# Encode message for sending
def encode_message(message_obj):
    return json.dumps(message_obj.to_dict()).encode('utf-8')

# Decode received message
def decode_message(message_bytes):
    message_dict = json.loads(message_bytes.decode('utf-8'))
    message = ChatMessage()
    message.from_dict(message_dict)
    return message

# Setting up server
host = '127.0.0.1'
port = 18000
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen()

# Store active users
clients = {}
max_users = 3

# Broadcast a message to all clients
def broadcast(message, exclude_client=None):
    for client in clients:
        if client != exclude_client:
            client.send(encode_message(message))

# Handle each client
def handle(client_socket):
    while True:
        try:
            message = decode_message(client_socket.recv(1024))

            # Handle report request
            if message.REPORT_REQUEST_FLAG == 1:
                response = ChatMessage()
                response.REPORT_RESPONSE_FLAG = 1
                response.NUMBER = len(clients)
                response.PAYLOAD = "\n".join([f"{username} at {addr[0]}:{addr[1]}" for (username, addr) in clients.values()])
                client_socket.send(encode_message(response))

            # Handle join request
            elif message.JOIN_REQUEST_FLAG == 1:
                if len(clients) >= max_users:
                    response = ChatMessage()
                    response.JOIN_REJECT_FLAG = 1
                    response.PAYLOAD = "Chatroom at full capacity."
                    client_socket.send(encode_message(response))
                elif any(user[0] == message.USERNAME for user in clients.values()):
                    response = ChatMessage()
                    response.JOIN_REJECT_FLAG = 1
                    response.PAYLOAD = "Username already in use."
                    client_socket.send(encode_message(response))
                else:
                    clients[client_socket] = (message.USERNAME, client_socket.getpeername())
                    response = ChatMessage()
                    response.JOIN_ACCEPT_FLAG = 1
                    response.USERNAME = message.USERNAME
                    response.PAYLOAD = "Welcome to the chatroom."
                    client_socket.send(encode_message(response))

                    # Notify all users of the new user joining
                    join_announcement = ChatMessage()
                    join_announcement.NEW_USER_FLAG = 1
                    join_announcement.USERNAME = message.USERNAME
                    join_announcement.PAYLOAD = f"{message.USERNAME} joined the chatroom."
                    broadcast(join_announcement, exclude_client=client_socket)

            # Handle quit request
            elif message.QUIT_REQUEST_FLAG == 1:
                username = clients.pop(client_socket, None)[0]
                if username:
                    quit_announcement = ChatMessage()
                    quit_announcement.QUIT_ACCEPT_FLAG = 1
                    quit_announcement.USERNAME = username
                    quit_announcement.PAYLOAD = f"{username} left the chatroom."
                    broadcast(quit_announcement)
                break

            # Broadcast any other payload as a message
            elif message.PAYLOAD:
                broadcast(message, exclude_client=client_socket)

        except Exception as e:
            print(f"Error handling client {clients.get(client_socket, ('Unknown',))[0]}: {e}")
            break

    # Close client connection
    client_socket.close()

# Accept new connections
def receive():
    while True:
        client_socket, client_address = server.accept()
        print(f"Connected with {str(client_address)}")

        # Initiate a new thread for each client
        thread = threading.Thread(target=handle, args=(client_socket,))
        thread.start()

print("Server is active and listening...")
receive()
