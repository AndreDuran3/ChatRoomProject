import socket
import threading
import json
from datetime import datetime

# Define a class for the message structure
class ChatMessage:
    def __init__(self):
        # Flags for different types of messages
        self.REPORT_REQUEST_FLAG = 0
        self.REPORT_RESPONSE_FLAG = 0
        self.JOIN_REQUEST_FLAG = 0
        self.JOIN_REJECT_FLAG = 0
        self.JOIN_ACCEPT_FLAG = 0
        self.NEW_USER_FLAG = 0
        self.QUIT_REQUEST_FLAG = 0
        self.QUIT_ACCEPT_FLAG = 0
        self.ATTACHMENT_FLAG = 0
        # Other fields for metadata
        self.NUMBER = 0
        self.USERNAME = ""
        self.FILENAME = ""
        self.PAYLOAD_LENGTH = 0
        self.PAYLOAD = ""

    def to_dict(self):
        # Convert object to a dictionary
        return self.__dict__

    def from_dict(self, message_dict):
        # Populate fields from a dictionary
        for key, value in message_dict.items():
            setattr(self, key, value)

# Function to encode message as JSON for network transmission
def encode_message(message_obj):
    return json.dumps(message_obj.to_dict()).encode('utf-8')

# Function to decode JSON message from network back into message object
def decode_message(message_bytes):
    if not message_bytes:
        return None  # Return None if the message is empty
    message_dict = json.loads(message_bytes.decode('utf-8'))
    message = ChatMessage()
    message.from_dict(message_dict)
    return message

# Set up the server
host = '127.0.0.1'
port = 18000
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen()

# Store active clients and their usernames
clients = {}
chat_history = []  # List to store chat history
max_users = 3

# Function to broadcast a message to all connected clients
def broadcast(message, exclude_client=None):
    for client in clients:
        if client != exclude_client:
            client.send(encode_message(message))

# Function to add a message to the chat history with a timestamp
def add_to_chat_history(username, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {username}: {content}"
    chat_history.append(formatted_message)

# Function to handle each client connection
def handle(client_socket):
    while True:
        try:
            message = decode_message(client_socket.recv(1024))  # Receive and decode message

            if message is None:
                continue  # Ignore if the message is empty or connection was interrupted

            # Handle each type of message based on flags
            if message.REPORT_REQUEST_FLAG == 1:
                # Report request: send the list of active users
                response = ChatMessage()
                response.REPORT_RESPONSE_FLAG = 1
                response.NUMBER = len(clients)
                response.PAYLOAD = "\n".join(
                    [f"{username} at {addr[0]}:{addr[1]}" for client, (username, addr) in clients.items()]
                )
                client_socket.send(encode_message(response))

            elif message.JOIN_REQUEST_FLAG == 1:
                # Check if the chatroom is full
                if len(clients) >= max_users:
                    response = ChatMessage()
                    response.JOIN_REJECT_FLAG = 1
                    response.PAYLOAD = "Chatroom at full capacity."
                    client_socket.send(encode_message(response))
                
                # Check if the username is already taken
                elif any(user[0] == message.USERNAME for user in clients.values()):
                    response = ChatMessage()
                    response.JOIN_REJECT_FLAG = 1
                    response.PAYLOAD = "Username already in use."
                    client_socket.send(encode_message(response))
                else:
                    # Accept the user into the chatroom
                    clients[client_socket] = (message.USERNAME, client_socket.getpeername())
                    response = ChatMessage()
                    response.JOIN_ACCEPT_FLAG = 1
                    response.USERNAME = message.USERNAME
                    response.PAYLOAD = "\n".join(chat_history)  # Send the chat history as payload
                    client_socket.send(encode_message(response))

                    # Announce to others that a new user joined
                    join_announcement = ChatMessage()
                    join_announcement.NEW_USER_FLAG = 1
                    join_announcement.USERNAME = message.USERNAME
                    join_announcement.PAYLOAD = f"{message.USERNAME} joined the chatroom."
                    broadcast(join_announcement, exclude_client=client_socket)

                    # Add join message to the chat history
                    add_to_chat_history("Server", f"{message.USERNAME} joined the chatroom.")

            elif message.QUIT_REQUEST_FLAG == 1:
                # Process user quitting
                if client_socket in clients:
                    username = clients.pop(client_socket)[0]
                    # Broadcast that the user left
                    quit_announcement = ChatMessage()
                    quit_announcement.QUIT_ACCEPT_FLAG = 1
                    quit_announcement.USERNAME = username
                    quit_announcement.PAYLOAD = f"{username} left the chatroom."
                    broadcast(quit_announcement)

                    # Add leave message to the chat history
                    add_to_chat_history("Server", f"{username} left the chatroom.")
                break

            elif message.PAYLOAD:
                # Handle a regular chat message and broadcast it
                username = clients[client_socket][0]  # Get the username of the sender
                add_to_chat_history(username, message.PAYLOAD)  # Add message to chat history
                broadcast(message, exclude_client=client_socket)  # Send message to others

        except Exception as e:
            print(f"Error handling client {clients.get(client_socket, ('Unknown',))[0]}: {e}")
            break

    # Close client connection when they disconnect
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
