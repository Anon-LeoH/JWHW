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
import pygtk
pygtk.require('2.0')
import gtk
import time

WaitChatPort = 51006
defualtChatPort = 52006

def get_time():
    tmp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
    tmp = "[" + tmp + "]"
    return tmp

class chatPage(object):
    def __init__(self, parent, name):
        self.name = name
        self.on = False
        self.parent = parent
        # main window part
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Chat with " + name)
        self.window.set_size_request(600,600)
        self.window.set_position(gtk.WIN_POS_CENTER)
        self.window.connect("destroy", self.close)
        # item part
        mainBox = gtk.VBox(False, 5)
        self.msgList, self.msgWindow = self.buildUpTxtArea()
        self.button = gtk.Button("Send")
        self.box1 = gtk.HBox(False, 5)
        self.msgText = gtk.Entry()
        self.msgWindow.set_size_request(580, 530)
        self.box1.set_size_request(580, 50)
        self.button.set_size_request(120, 30)
        self.msgText.set_size_request(460, 40)        
        # attributes part
        self.button.connect("clicked", self.sendMsg, self.msgText)
        self.msgText.connect("activate", self.sendMsg, self.msgText)
        self.box1.add(self.msgText)
        self.box1.add(self.button)
        mainBox.add(self.msgWindow)
        mainBox.add(self.box1)
        self.window.add(mainBox)

    def onOrNot(self):
        return self.on

    def buildUpTxtArea(self):
        area = gtk.TextView()
        area.set_editable(False)
        swindow = gtk.ScrolledWindow()
        swindow.add(area)
        buf = area.get_buffer()
        buf.create_mark("end", buf.get_end_iter(), False)
        return area, swindow

    def insertOneMsg(self, txtArea, msg, name):
        if msg == "" or msg.strip() == "":
            return
        msg = get_time() + " " + name + ": " + msg
        buf = txtArea.get_buffer()
        mark = buf.get_mark("end")
        itr = buf.get_iter_at_mark(mark)
        buf.insert(itr, "\n")
        buf.insert(itr, msg)
        txtArea.scroll_mark_onscreen(mark)

    def getMsg(self, msg):
        self.insertOneMsg(self.msgList, msg, self.name)

    def sendMsg(self, widget, data):
        msg = data.get_text()
        data.set_text("")
        self.parent.sendChat(json.dumps({
                                    'type': 'chat',
                                    'from': self.parent.username,
                                    'to': self.name,
                                    'msg': msg,
                             }))
        self.insertOneMsg(self.msgList, msg, self.parent.username)

    def show(self):
        try: 
            self.on = True
            self.window.show_all()
            gtk.main()
        except:
            self.close(None)

    def close(self, widget, data = None):
        self.on = False
        gtk.main_quit()

class ChatClientWindow(Tkinter.Frame):
    def __init__(self, parent, sock, user_key, username):
        Tkinter.Frame.__init__(self, parent)
        self.parent = parent
        self.s = sock
        self.number = 0;
        self.chatWindow = {}
        self.user_key = user_key  # 用户标识符，供服务器验证客户端的身份
        self.username = username
        self.uList = {}
        self.init_ui()
        self.pack()

        self.running = True  # 运行状态，供监听线程使用
        self.bind('<Destroy>', lambda e: self.stop_running())
        self.recieve_thread = threading.Thread(None, lambda: self.receiveMsg())
        self.recieve_thread.start()  # 启动监听线程

    def stop_running(self):
        self.running = False
        self.s.close()

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

    def sendChat(self, msg):
        try:
            self.s.send(msg)
        except socket.error as e:
            tkMessageBox.showerror('Error', 'Error occured!\n' + str(e))

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
                        if not uname in self.uList:
                            tkMessageBox.showerror('Error', 'Error occured!\n' + 'No such user!')
                            self.msg_str.set('')
                            return
                        if uname == self.username:
                            tkMessageBox.showerror('Error', 'Error occured!\n' + 'Cannot talk to yourself!')
                            self.msg_str.set('')
                            return
                        else:
                            self.sendChat(json.dumps({
                                    'type': 'chat',
                                    'from': self.username,
                                    'to': uname,
                                    'msg': ' ',
                            }))
                            if uname not in self.chatWindow:
                                self.chatWindow[uname] = chatPage(self, uname)
                            if not self.chatWindow[uname].on:
                                self.chatWindow[uname] = chatPage(self, uname)
                                tmp = threading.Thread(None, lambda: self.chatWindow[uname].show())
                                tmp.start()                                                   
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
                    obj = None
                    try:
                        obj = json.loads(data)
                    except ValueError as e:
                        print data
                        print obj
                        print e
                        data = data.split("}{")
                        data = data[0] + "}"
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
                        elif obj['errno'] == 3:
                            fr = obj['from']
                            msg = obj['msg']
                            if fr not in self.chatWindow:
                                self.chatWindow[fr] = chatPage(self, fr)
                            if not self.chatWindow[fr].on:
                                self.chatWindow[fr] = chatPage(self, fr)
                                tmp = threading.Thread(None, lambda: self.chatWindow[fr].show())
                                tmp.start()
                            while not self.chatWindow[fr].on:
                                pass
                            self.chatWindow[fr].getMsg(msg)
                    except KeyError:
                        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')                                
                        log = '[{}] [{} from {}]: {}\n'.format(now,
                                                               "Broadcast",
                                                               obj['user'].encode('utf8'),
                                                               obj['msg'].encode('utf8'))
                        self.log.insert('end', log)
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
