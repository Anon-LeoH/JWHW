Miliao
========

Homework of computer network

###Structure
The structure of the chat system.

####Functional Structure
* Client\_Version2  The version with private chat UI and two added function
* Server            The version which can support any version of client

###Environment
The test environment is Ubuntu LTS12.04.
Tested on a network made up by three computer.

####Setup
Use the below command to setup the environment.

````bash
$ sudo apt-get update
$ sudo apt-get install python-tk
````

###Useage

####Server
````bash
$ python ./Server/server.py
````

####Client
````bash
$ python ./Client_Version2/client.py
````
####Function
* :ul                Get online user list
* :chat xxx          Change to private chat with xxx
* :return            Return to broadcast mode(_Only when private chat_)
* \\_facemoodcode_   Will be replaced by facemood.

###Notice
These two version are both not stable. As the socket of private chat is
blocking, there may exist some packet drop during the chat. It is OK when you
notice some warning in the terminal. If there are bugs exised, please let me
know and I'll make some improvement.

###Technique Useage
* python2.7
* Tkinter
* socket(select)

###Bug Report
_lyu159494@gmail.com_

