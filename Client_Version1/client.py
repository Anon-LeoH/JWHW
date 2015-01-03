#!/usr/bin/env python2
# -*- encoding: utf8 -*-
import Tkinter
import tkMessageBox
import ttk
from ScrolledText import ScrolledText
import socket
import json
from datetime import datetime
from select import select
import shelve
import uuid
import threading

WaitChatPort = 51006
defualtChatPort = 52006

class PrivateServer():
    def __init__(self, parent):
        self.read = []
        self.write = []
        self.dic = {}
        self.parent = parent
        self.running = False

    def adds(self, name, s):
        print "oops!"
        if name in self.dic:
            return False
        else:
            self.read.append(s)
            self.write.append(s)
            self.dic[name] = s
            return True

    def removes(self, name):
        if name not in self.dic:
            return False
        else:
            del self.dic[name]

    def inServer(self, name):
        if name in self.dic:
            return True
        else:
            return False

    def send(self, name, data):
        if name not in self.dic:
            return
        else:
           try:
               self.dic[name].send(data)
           except socket.error as e:
               tkMessageBox.showerror('Error', 'Error occured!\n' + str(e))

    def work(self):
        self.running = True
        try:
            R = self.read
            W = self.write

            while self.running:
                r, w, e = select(R, W, R, 0.1)
                msg_list = self.readInSelect(R, W, r)
                for msg in msg_list:
                    self.parent.insertMsg(msg, "Private Chat")
                for s in e:
                    self.disconnect(R, W, s)

        except socket.timeout:
            pass  # 忽略超时
        except socket.error as e:
            print e
        
        for s in self.read:
            s.close()
        for s in self.write:
            s.close()

    def readInSelect(self, R, W, r):
        msg_list = []
        for s in r:
            try:
                msg = s.recv(1024)
                print "here 1"
                if len(msg):
                    msg_obj = json.loads(msg.decode('utf8'))                            
                    msg_list.append(msg_obj)
                    print "here 2"
                else:
                    self.disconnect(R, W, s)
            except socket.error as e:
                print "type 1"
                print e
                self.disconnect(R, W, s)
            except (KeyError, ValueError) as e:  # 消息无效，丢弃
                print "type 2"
                print e

        return msg_list

    def disconnect(self, R, W, s):
        for name in self.dic:
            if self.dic[name] == s:
                del self.dic[name]
                break
        R.remove(s)
        W.remove(s)
        s.close()

    

class ChatClientWindow(Tkinter.Frame):
    def __init__(self, parent, sock, user_key, username):
        Tkinter.Frame.__init__(self, parent)
        self.parent = parent
        self.s = sock
        self.number = 0;
        self.cp = 48000
        self.user_key = user_key  # 用户标识符，供服务器验证客户端的身份
        self.username = username
        self.uList = {}
        self.server = PrivateServer(self)
        self.init_ui()
        self.ws = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ws.bind(('127.0.0.1', WaitChatPort))
        self.pack()

        self.running = True  # 运行状态，供监听线程使用
        self.bind('<Destroy>', lambda e: self.stop_running())
        self.recieve_thread = threading.Thread(None, lambda: self.receiveMsg())
        self.recieve_thread.start()  # 启动监听线程
        self.recieve_thread2 = threading.Thread(None, lambda: self.receiveChat())
        self.recieve_thread2.start()  # 启动监听线程
        self.recieve_thread3 = threading.Thread(None, lambda: self.server.work())
        self.recieve_thread3.start()

    def stop_running(self):
        self.running = False
        self.server.running = False
        self.ws.settimeout(0.01)
        self.ws.close()
        self.s.close()

    def receiveChat(self):
        self.ws.listen(10)
        while self.running:
            tmp = self.ws.accept()
            ip = tmp[1][0]
            tmp = tmp[0]
            for un in self.uList:
                if self.uList[un] == ip:
                    self.server.adds(un, tmp)
                    self.server.send(un, "")
                    break

    def init_ui(self):
        self.parent.title('Chat - %s' % self.username)

        self.log = ScrolledText(self)
        self.log.grid(column=0, row=0, columnspan=2, sticky='NSEW')

        send = ttk.Button(self, text='Send', command=lambda: self.onSend())
        send.grid(column=1, row=1, sticky='NSEW', padx=5, pady=5)

        self.msg_str = Tkinter.StringVar()
        msg = ttk.Entry(self, textvariable=self.msg_str)
        msg.bind('<KeyRelease>',
                 lambda e: send.invoke() if e.keysym == 'Return' else None)
        msg.grid(column=0, row=1, sticky='NSEW', pady=5)

        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)

    def onSend(self):
        msg = self.msg_str.get()
        if len(msg) == 0:
            return
        try:
            if msg.index(':') == 0:
                if msg.index('ul') == 1:
                    try:
                        self.s.send(json.dumps({
                            'type': 'usrList',
                            'user_key': self.user_key,
                        }))
                    except socket.error as e:
                        tkMessageBox.showerror('Error', 'Error occured!\n' + str(e))
        except ValueError as e:
            try:
                if msg.index(':') == 0:
                    if msg.index('chat') == 1:
                        uname = msg.strip().split(' ')[1]
                        data = msg.strip().split(' ')[2]
                        if not uname in self.uList:
                            tkMessageBox.showerror('Error', 'Error occured!\n' + 'No such user!')
                        if uname == self.username:
                            tkMessageBox.showerror('Error', 'Error occured!\n' + 'Cannot talk to yourself!')
                        else:
                            if not self.server.inServer(uname):
                                tmp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                tmp.connect((self.uList[uname], WaitChatPort))
                                self.server.send(uname, "")
                                self.server.adds(uname, tmp)
                            self.server.send(uname, json.dumps({
                                'user': uname,
                                'msg': data,
                            }))                            
            except ValueError:
                try:
                    self.s.send(json.dumps({
                        'type': 'msg',
                        'msg': msg,
                        'user_key': self.user_key,
                    }))
                except socket.error as e:
                    tkMessageBox.showerror('Error', 'Error occured!\n' + str(e))

        self.msg_str.set('')

    def receiveMsg(self):
        while self.running:
            try:
                data = self.s.recv(1024)  # 阻塞接收，有超时时间
                if len(data):
                    obj = json.loads(data)
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    try:
                        if obj['errno'] == 0:
                            un = obj['users']
                            ss = obj['ips']
                            for i in xrange(len(un)):
                                self.uList[un[i]] = ss[i]
                            log = '[{}] {}:\n'.format(now, 'UserList')
                            for u in un:
                                log += u + "\n"
                            self.log.insert('end', log)
                    except KeyError:
                        self.insertMsg(obj, "Broadcast")
                else:
                    tkMessageBox.showerror('Error', 'Connection closed.')
                    self.running = False
            except socket.timeout:
                pass  # 超时，忽略
            except socket.error as e:
                if not self.running:
                    return
                tkMessageBox.showerror('Error', 'Error occured!\n' + str(e))
                self.running = False

    def insertMsg(self, obj, option):   
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')                                
        log = '[{}] [{} from {}]: {}\n'.format(now,
                                               option,
                                               obj['user'].encode('utf8'),
                                               obj['msg'].encode('utf8'))
        self.log.insert('end', log)
    

class LoginDialog(Tkinter.Frame):
    def __init__(self, parent):
        Tkinter.Frame.__init__(self, parent)
        self.parent = parent
        self.s = None
        self.init_ui()
        self.pack()

    def init_ui(self):
        self.parent.title('Chat - Login')

        server_label = ttk.Label(self, text='Server')
        server_label.grid(column=0, row=0, sticky='NSW')

        self.server_str = Tkinter.StringVar()
        server = ttk.Entry(self, textvariable=self.server_str)
        server.grid(column=1, row=0, sticky='NSEW')
        self.server_str.set('localhost:5555')

        username_label = ttk.Label(self, text='Username')
        username_label.grid(column=0, row=1, sticky='NSW')

        self.username_str = Tkinter.StringVar()
        username = ttk.Entry(self, textvariable=self.username_str)
        username.grid(column=1, row=1, sticky='NSEW')

        password_label = ttk.Label(self, text='Password')
        password_label.grid(column=0, row=2, sticky='NSW')

        self.password_str = Tkinter.StringVar()
        password = ttk.Entry(self, textvariable=self.password_str, show='*')
        password.grid(column=1, row=2, sticky='NSW')

        buttons_frame = ttk.Frame(self)
        buttons_frame.grid(column=0, row=3, columnspan=2, sticky='NSWE')

        login = ttk.Button(buttons_frame, text='Login',
                           command=lambda: self.onLogin())
        login.grid(column=0, row=0, padx=10, pady=5)

        register = ttk.Button(buttons_frame, text='Register',
                              command=lambda: self.onRegister())
        register.grid(column=1, row=0, padx=10, pady=5)

        self.parent.resizable(False, False)

    def onLogin(self):
        username = self.username_str.get()
        password = self.password_str.get()
        if len(username) == 0 or len(password) == 0:
            tkMessageBox.showerror('Error',
                                   'Username and password are required.')
            return
        if self.s is None and self.connect() is False:
            return

        try:
            self.s.send(json.dumps({
                'type': 'login',
                'username': username,
                'password': password,
            }))

            respon = self.s.recv(1024)
            respon_obj = json.loads(respon)
            if respon_obj['errno'] == 0:
                # 登录成功
                tkMessageBox.showinfo('Success', 'Login success!')
                ChatClientWindow(self.parent, self.s, respon_obj['user_key'],
                                 username)
                self.destroy()
            else:
                # 登录失败
                tkMessageBox.showerror('Error',
                                       'Failed!\n' + respon_obj['msg'])
        except socket.error as e:
            tkMessageBox.showerror('Error', 'Error occured!\n' + str(e))

    def onRegister(self):
        username = self.username_str.get()
        password = self.password_str.get()
        if len(username) == 0 or len(password) == 0:
            tkMessageBox.showerror('Error',
                                   'Username and password are required.')
            return
        if self.s is None and self.connect() is False:
            return

        try:
            self.s.send(json.dumps({
                'type': 'register',
                'username': username,
                'password': password,
            }))

            respon = self.s.recv(1024)
            respon_obj = json.loads(respon)
            if respon_obj['errno'] == 0:
                # 注册成功
                tkMessageBox.showinfo('Success', 'Register success!')
            else:
                # 注册失败
                tkMessageBox.showerror('Error',
                                       'Failed!\n' + respon_obj['msg'])
        except socket.error as e:
            tkMessageBox.showerror('Error', 'Error occured!\n' + str(e))

    def connect(self):
        host = self.server_str.get().split(':')
        try:
            ip = socket.gethostbyname(host[0])  # 若不是IP则进行解析
            port = int(host[1])
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.settimeout(0.1)
            self.s.connect((ip, port))
        except (KeyError, ValueError, socket.gaierror):
            tkMessageBox.showerror('Error', 'Invalid server!')
            return False
        except socket.error as e:
            tkMessageBox.showerror('Error',
                                   'Failed to connect to server!\n' + str(e))
            return False
        return True


if __name__ == '__main__':
    app = Tkinter.Tk()
    LoginDialog(app)
    app.mainloop()
