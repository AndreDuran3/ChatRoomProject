import socket
import threading
import json
import time

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
    if not message_bytes:
        return None  # Return None if message is empty
    message_dict = json.loads(message_bytes.decode('utf-8'))
    message = ChatMessage()
    message.from_dict(message_dict)
    return message

# Define client connection
def create_connection():
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(('127.0.0.1', 18000))
    return client

client = create_connection()
in_chatroom = False  # State variable to track if the client is in the chatroom
client_connected = True  # Track if the client is connected to the server
nickname = ""  # Initialize nickname as an empty string

# Function to handle receiving messages from the server
def receive():
    global in_chatroom, client_connected, client
    while client_connected:
        try:
            message_bytes = client.recv(1024)
            message = decode_message(message_bytes)

            # Process messages based on flags
            if message:
                if message.REPORT_RESPONSE_FLAG == 1:
                    print(f"\nThere are {message.NUMBER} active users:")
                    print(message.PAYLOAD)

                elif message.JOIN_ACCEPT_FLAG == 1:
                    print("\nSuccessfully joined the chatroom.")
                    print("Chat history:")
                    print(message.PAYLOAD)
                    in_chatroom = True  # Switch to chatroom mode
                    # Display one-time message upon entering chatroom
                    print("\nYou are now in a chatroom, enter 'q' to leave.")

                elif message.JOIN_REJECT_FLAG == 1:
                    print("\nJoin request rejected:", message.PAYLOAD)
                    in_chatroom = False  # Return to main menu if join is rejected

                elif message.NEW_USER_FLAG == 1:
                    print(f"\n{message.USERNAME} joined the chatroom.")

                elif message.QUIT_ACCEPT_FLAG == 1:
                    print(f"\n{message.USERNAME} left the chatroom.")
                    in_chatroom = False  # Set client out of chatroom mode

                elif message.PAYLOAD:
                    print(f"\n{message.PAYLOAD}")

        except (ConnectionResetError, ConnectionAbortedError):
            # Attempt to reconnect if the connection was lost unintentionally
            print("Connection lost. Attempting to reconnect...")
            client = create_connection()
            if in_chatroom:
                # Rejoin the chatroom if disconnected unintentionally
                join_message = ChatMessage()
                join_message.JOIN_REQUEST_FLAG = 1
                join_message.USERNAME = nickname
                client.send(encode_message(join_message))
            time.sleep(2)

# Function to handle sending messages to the server
def send_message():
    global in_chatroom, client_connected, nickname, client
    while client_connected:
        if not in_chatroom:
            # Show menu only if not in the chatroom
            print("\nMenu:\n1. Get chatroom report\n2. Join chatroom\n3. Disconnect from server")
            choice = input("Your choice: ")

            if choice == '1':
                if client_connected:
                    message = ChatMessage()
                    message.REPORT_REQUEST_FLAG = 1
                    client.send(encode_message(message))

            elif choice == '2':
                # Ask for a username before sending the join request
                nickname = input("Enter a username to join the chatroom: ")
                if client_connected:
                    join_message = ChatMessage()
                    join_message.JOIN_REQUEST_FLAG = 1
                    join_message.USERNAME = nickname
                    client.send(encode_message(join_message))
                    in_chatroom = True  # Prevents menu re-prompting until response

            elif choice == '3':
                if client_connected:
                    quit_message = ChatMessage()
                    quit_message.QUIT_REQUEST_FLAG = 1
                    quit_message.USERNAME = nickname
                    client.send(encode_message(quit_message))
                    client_connected = False
                    client.close()
                    print("Disconnected from the server.")
            else:
                print("Invalid choice. Please try again.")
        
        else:
            # In chatroom mode - only prompt for input without repeating instructions
            message_text = input()
            if message_text.lower() == 'q' and client_connected:
                # Send quit request to the server
                quit_message = ChatMessage()
                quit_message.QUIT_REQUEST_FLAG = 1
                quit_message.USERNAME = nickname
                client.send(encode_message(quit_message))
                print("Exiting chatroom. Returning to main menu.")
                in_chatroom = False  # Return to menu mode
            elif client_connected:
                # Send chat message
                chat_message = ChatMessage()
                chat_message.PAYLOAD = f"{nickname}: {message_text}"
                client.send(encode_message(chat_message))

# Start threads for receiving and sending messages
receive_thread = threading.Thread(target=receive)
receive_thread.start()

send_thread = threading.Thread(target=send_message)
send_thread.start()