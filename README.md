Miliao
========

Homework of computer network

###Structure
The structure of the chat system.

####Functional Structure
* Client\_Vertion1  The version without private chat UI
* Client\_Version2  The version with private chat UI
* Server            The version which can support both version of client

###Environment
The test environment is Ubuntu LTS12.04.
Tested on a network made up by three computer.

####Setup
Use the below command to setup the environment.

````bash
$ sudo apt-get update
$ sudo apt-get install python-gtk\*
$ sudo apt-get install python-tk
````

###Useage

####Server
````bash
$ python server.py
````

####Client Version1
````bash
$ python client.py
````

As in the client UI view, input _":ul"_ to get the user list, and _":chat xxx
sth."_ to send sth. to xxx. Type something else to broadcast it.

####Client Version2
````bash
$ python client.py
````

As in the client UI view, type something to broadcast it.
Input _":ul"_ to get the user list, and _":chat xxx"_ to open the chat window.
And type anything in the chat window to send.

###Notice
These two version are both not stable. As the socket of private chat is
blocking, there may exist some packet drop during the chat. It is OK when you
notice some warning in the terminal. If there are bugs exised, please let me
know and I'll make some improvement.

###Technique Useage
* python2.7
* pyGtk
* Tkinter
* socket(select)

###Bug Report
_lyu159494@gmail.com_

