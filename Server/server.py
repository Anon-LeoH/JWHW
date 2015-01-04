#!/usr/bin/env python2
# -*- encoding: utf8 -*-
import Tkinter
from ScrolledText import ScrolledText
import json
import socket
from select import select
import shelve
import uuid
import threading
from datetime import datetime


class ChatServer(object):
    USERDB = 'user.db'

    def __init__(self, ui, address='', port=5555):
        self.ui = ui
        self.msgs = {}
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind((address, port))
        self.s.setblocking(0)  # 非阻塞IO
        self.running = False

    def start(self):
        self.userdb = shelve.open(self.USERDB)
        self.users = {}
        self.room = {}
        self.s.listen(5)
        self.ui.info('Started', 'Server')
        self.running = True
        self.work()

    def stop(self):
        self.running = False
        self.s.close()

    def work(self):
        try:
            R = [self.s]
            W = []

            while self.running:
                r, w, e = select(R, W, R, 0.1)
                msg_list = self.readInSelect(R, W, r)

                if len(msg_list):
                    self.writeInSelect(R, W, w, msg_list)

                for s in e:
                    self.ui.warn('Client error', s.getpeername())
                    self.disconnect(R, W, s)

        except socket.timeout:
            pass  # 忽略超时
        except socket.error as e:
            self.ui.error('Error occured: ' + str(e), 'Server')
        finally:
            self.s.close()

    def readInSelect(self, R, W, r):
        msg_list = []
        for s in r:
            if s is self.s:  # 服务器socket，接受用户连接
                client_s = s.accept()
                R.append(client_s[0])
                W.append(client_s[0])
                self.ui.info('Client connected', client_s[1])
            else:  # 客户端socket，接受客户端消息
                try:
                    msg = s.recv(1024)
                    if len(msg):
                        msg_obj = json.loads(msg.decode('utf8'))

                        if msg_obj['type'] == 'login':  # 用户登陆
                            resp = self.login(s,
                                              msg_obj['username'],
                                              msg_obj['password'])
                            s.send(json.dumps(resp).encode('utf8'))

                        elif msg_obj['type'] == 'msgs':
                             if msg_obj['username'] in self.msgs and self.msgs[msg_obj['username']] != None:
                                 tmp = { "errno": 4,
                                         "msgs": str(self.msgs[msg_obj['username']])}
                                 s.send(json.dumps(tmp).encode('utf8'))
                                 self.msgs[msg_obj['username']] != None

                        elif msg_obj['type'] == 'register':  # 用户注册
                            resp = self.register(s,
                                                 msg_obj['username'],
                                                 msg_obj['password'])
                            s.send(json.dumps(resp).encode('utf8'))

                        elif msg_obj['type'] == 'usrList':  # 用户获取
                            tmp = { "errno": 0, 
                                    "users": [self.users[t][1].decode('utf8') for t in self.users],
                                    "ips": [t.getsockname()[0] for t in self.users] }
                            s.send(json.dumps(tmp).encode('utf8'))

                        elif msg_obj['type'] == 'chat':  # 私聊
                            uname = msg_obj['to']
                            fr = msg_obj['from']
                            t = None
                            for sock in self.users:
                                if self.users[sock][1] == uname:
                                    t = sock
                                    msg = msg_obj['msg']
                                    tmp = { "errno": 3, 
                                            "from": fr,
                                            "msg": msg }
                                    t.send(json.dumps(tmp).encode('utf8'))
                                    break
                            else:
                                if uname not in self.msgs or self.msgs[uname] == None:
                                    self.msgs[uname] = []
                                msg = msg_obj['msg']
                                tmp = { "from": fr,
                                        "msg": msg,
                                        "time": msg_obj['time']}
                                self.msgs[uname].append(tmp)
                        
                        else:  # 用户发送消息
                            if s not in self.users or \
                                    self.users[s][0] != msg_obj['user_key']:
                                raise ValueError('Unauthorized user')
                            
                            msg_obj['user'] = self.users[s][1].decode('utf8')
                            msg_list.append(msg_obj)
                            self.ui.info('%s: %s' % (
                                         msg_obj['user'],
                                         msg_obj['msg']),
                                         s.getpeername())

                    else:
                        self.disconnect(R, W, s)

                except socket.error as e:
                    self.ui.warn('Receive error, drop the client (%s)'
                                 % str(e))
                    self.disconnect(R, W, s)

                except (KeyError, ValueError) as e:  # 消息无效，丢弃
                    self.ui.warn('Discard message (%s)' % str(e))

        return msg_list

    def writeInSelect(self, R, W, w, msg_list):
        for s in w:
            try:
                for msg in msg_list:  # 把消息广播到每个用户
                    s.send(json.dumps({
                        'user': msg['user'],
                        'msg': msg.get('msg', ''),
                    }))
            except socket.error as e:
                self.ui.warn('Send error, drop the client (%s)', str(e))

    def disconnect(self, R, W, s):
        user = self.users.pop(s, None)
        self.msgs[user[1]] = []
        if user is not None:
            self.ui.removeUser(user[1])  # user[1]为用户名
            self.ui.info('Logout.', user[1])
        R.remove(s)
        W.remove(s)
        self.ui.info('Disconnected.', s.getpeername())
        s.close()

    def login(self, sock, username, password):
        username = username.encode('utf8')
        if self.userdb.get(username, None) == password:  # 检查用户密码
            user_key = uuid.uuid4().hex  # 登陆成功，生成随机数用来做用户认证
            self.users[sock] = (user_key, username)
            self.ui.addUser(username)
            self.ui.info('%s login successed.' % username,
                         sock.getpeername())
            return {'errno': 0, 'user_key': user_key}
        else:
            self.ui.warn('%s login failed.' % username, sock.getpeername())
            return {'errno': -1, 'msg': 'Wrong username or password'}

    def register(self, sock, username, password):
        username = username.encode('utf8')
        if username in self.userdb:  # 检查用户名冲突
            self.ui.warn('Try to register as %s but failed.' % username,
                         sock.getpeername())
            return {'errno': -1, 'msg': 'The username has been used'}
        else:
            self.userdb[username] = password
            self.userdb.sync()
            self.ui.info('%s registered successfully.' % username,
                         sock.getpeername())
            return {'errno': 0}


class ServerUI(Tkinter.Tk):
    def __init__(self):
        Tkinter.Tk.__init__(self)
        self.init_ui()

    def init_ui(self):
        self.title('MiLiao - Server')

        self.log = ScrolledText(self)
        self.log.grid(column=0, row=0, sticky='NSWE')

        self.user_list = Tkinter.Listbox(self)
        self.user_list.grid(column=1, row=0, sticky='NSWE')

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)

    def addLog(self, level, msg, obj):
        log_msg = '[%s][%s] [%s] %s\n' % (
            level, datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            obj, msg)
        self.log.insert('end', log_msg)

    def info(self, msg, obj=None):
        self.addLog('info', msg, obj or '')

    def warn(self, msg, obj=None):
        self.addLog('warn', msg, obj or '')

    def error(self, msg, obj=None):
        self.addLog('error', msg, obj or '')

    def addUser(self, user):
        self.user_list.insert('end', user)

    def removeUser(self, user):
        user = user.decode('utf8')
        for i, u in enumerate(self.user_list.get(0, 'end')):
            if user == u:
                self.user_list.delete(i)
                break


if __name__ == '__main__':
    ui = ServerUI()
    server = ChatServer(ui)
    ui.bind('<Destroy>', lambda e: server.stop())
    server_thread = threading.Thread(target=server.start)
    server_thread.start()
    ui.mainloop()
