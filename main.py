import os
from random import randrange
import requests
import json
import time
import pprint
from datetime import datetime
from types import SimpleNamespace

IS_DEBUG_MODE = False

class Inbox:
    _owner = dict
    _threads = []

    def __init__(self, owner = dict(), threads = list):
        self._owner = owner
        self._threads = threads

    def getThreadById(self, thread_id: str) -> dict:
        for thread in self._threads:
            if hasattr(thread, 'thread_id'):
                if (thread.thread_id == thread_id):
                    return thread

    def setThreads(self, threads: list) -> None:
        self._threads = threads

    def setOwner(self, str: str) -> None:
        self._owner = str

    def getOwner(self) -> dict:
        return self._owner

    def getThreads(self) -> list:
        return self._threads

class Auth:
    _auth_cookie = ""
    _instagram_app_id = ""

    def __init__(self, input_auth_cookie = '', input_instagram_app_id = ''):
        self._auth_cookie = input_auth_cookie
        self._instagram_app_id = input_instagram_app_id
    
    def setAuthCookie(self, str: str) -> None:
        self._auth_cookie = str

    def setInstagramAppId(self, str: str) -> None:
        self._instagram_app_id = str

    def getHeaders(self) -> dict:
        headers_dict = {
            'x-ig-app-id': self._instagram_app_id,
            'cookie': self._auth_cookie
        }

        return headers_dict

    def hasHeaders(self) -> bool:
        return len(self._instagram_app_id) > 0 and len(self._auth_cookie) > 0

AUTH = Auth()
MAX_THREADS = 100
MAX_MESSAGES_PER_THREAD = 1

INBOX = Inbox()

def getParsedResponse(responseText: str) -> dict:
    return json.loads(responseText, object_hook=lambda d: SimpleNamespace(**d))

def getPaginatedThreadMessages(thread: str, cursor: str) -> list:
    if IS_DEBUG_MODE: print(f"DEBUG --> Attempting to fetch from cursor: {cursor}")
    
    url = f'https://i.instagram.com/api/v1/direct_v2/threads/{thread}/?cursor={cursor}'
    messages = []
    req = requests.get(url, headers = AUTH.getHeaders())
    
    if (req.ok):
        data = getParsedResponse(req.text) 
        payload_thread = data.thread
        items = payload_thread.items
        for item in items:
            if hasattr(item, 'text'):
                if IS_DEBUG_MODE: print(f"DEBUG --> Message id {item.item_id} found! Retrieving...")

                me = payload_thread.inviter.full_name
                other = payload_thread.users[0].full_name

                messages.append({
                    "item_id": item.item_id,
                    "message": item.text,
                    "when": datetime.utcfromtimestamp((int(item.timestamp) / 1000000)).strftime("%d-%m-%Y %H:%M:%S"),
                    "sender": me if item.is_sent_by_viewer else other
                })

    return messages

def processThreadMessages(thread: str, cursor: str, filename: str, loading_message: str):
    all_messages = []

    start_time = time.time()
    while True:
        if not IS_DEBUG_MODE:
            refreshMenu()
            qtd_dots = randrange(3, 6)
            dots = ""

            for _ in range(qtd_dots):
                dots = dots + "."
            print(f"{loading_message}{dots}")

        new_messages = getPaginatedThreadMessages(thread, cursor)

        if (len(new_messages) > 0):
            all_messages = all_messages + new_messages
            last_msg = new_messages[-1]
            cursor = last_msg["item_id"]

            if IS_DEBUG_MODE: print(f"DEBUG --> Cursor update with {cursor}, fetching again!")
        else:
            if IS_DEBUG_MODE: print(f"DEBUG --> Fetch finished!")
            break

    fMessage = ""

    if IS_DEBUG_MODE: print("DEBUG --> Writing messages to file...")
    for message in all_messages:
        when = message["when"]
        sender = message["sender"]
        text = message["message"]
        fMessage = fMessage + f"{when} --> {sender}: {text}\n"

    file = open(f"{filename}.txt", "w");
    file.write(fMessage)

    count_messages_fetched = len(all_messages)
    runtime = round(time.time() - start_time, 2)

    if IS_DEBUG_MODE: print(f"DEBUG --> {count_messages_fetched} messages written sucessfully to file in {runtime} seconds...")
    file.close()

def getInbox() -> dict:
    url = f"https://i.instagram.com/api/v1/direct_v2/inbox/?persistentBadging=true&folder=&limit={MAX_THREADS}&thread_message_limit={MAX_MESSAGES_PER_THREAD}"
    req = requests.get(url, headers=AUTH.getHeaders())

    try:
        response = getParsedResponse(req.text)
        return response
    except:
        input("Invalid credentials! Press any key to go back to main menu!\n")
        menu()

def refreshMenu() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')
    li = "----------------->"
    ri = "<-----------------"
    print(f"{li} INSTAGRAM DM RETRIEVER V1.0 {ri}\n")

def loadingMenu() -> None:
    refreshMenu()
    print("Loading inbox...\n")

def authenticationMenu() -> None:
    refreshMenu()
    print("Please, insert the autentication cookie: \n")
    auth_cookie = input("--> ")

    refreshMenu()
    print("Please, insert the instagram app ID: \n ")
    instagram_app_id = input("--> ")

    AUTH.setAuthCookie(auth_cookie)
    AUTH.setInstagramAppId(instagram_app_id)
    menu()

def inboxMenu(refresh_inbox = True) -> None:
    if not AUTH.hasHeaders():
        menu()

    loadingMenu()
    
    if refresh_inbox:
        inboxResponse = getInbox()
        INBOX.setOwner(inboxResponse.viewer)
        INBOX.setThreads(inboxResponse.inbox.threads)
    
    print(f"Select one of the following threads by ID:\n")
    index_thread_id_mapping = []
    for index, thread in enumerate(INBOX.getThreads()):
        index_thread_id_mapping.append({ 
            'index': index + 1, 
            'thread_id': thread.thread_id 
        })
        print(f"{index + 1} --> {thread.thread_title}")

    selected_id = input("\n--> ")
    selected_thread = None

    for thread_map in index_thread_id_mapping:
        if (int(selected_id) == int(thread_map.get("index"))):
            selected_thread = INBOX.getThreadById(thread_map.get("thread_id"))

    if (selected_thread is None):
        print(f"Couldn't find the thread by ID {selected_id}!\n")
        input("Enter to try again...")
        inboxMenu(False)
    else:
        thread_title = selected_thread.thread_title
        loading_message = f"Downloading messages from thread {selected_id}: {thread_title}"
        thread_item = selected_thread.items[0]
        filename = f"messages_between_{selected_thread.users[0].username}_and_{INBOX.getOwner().username}"
        processThreadMessages(selected_thread.thread_id, thread_item.item_id, filename, loading_message)
        print(f"Processing finished! See the results on the created file: {filename}.\n")
        print("Do you wish to download another thread? (y/n)\n")
        start_again = input("--> ")

        if (start_again == "y"):
            inboxMenu(False)
        else: 
            menu()

def menu():
    refreshMenu()
    print("1 --> Authenticate")
    print("2 --> Inbox\n")

    if not AUTH.hasHeaders():
        print("You're not authenticated!\n")
    
    opt = input("Insert the option: ")

    if (opt == "1"):
        authenticationMenu()
        return

    if (opt == "2"):
        inboxMenu()
        return

    menu()

menu()
