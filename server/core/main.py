import socket
import json
import configparser
import hashlib
import os
import subprocess
import time
from conf import setting

class FTPServer(object):
    STATUS_CODE ={
        200:"success auth",
        201:'username or password error',
        301:'file exits',
        300:'file not exits',
        302:'this msg include the msg size',
        350:'dir changed',
        351:'dir not exist'
    }

    MSG_SIZE = 1024 #消息最常1024

    def __init__(self,managent_instance):
        self.mangent_instance = managent_instance
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.socket.bind((setting.HOST,setting.PORT))
        self.socket.listen(setting.MAX_SOCKET_LISTEN)
        self.accounts = self.load_accounts()
        self.user_obj = None
        self.user_current_dir = None

    def run_forever(self):
        print('starting FTP server on %s:%s'.center(50,'-') % (setting.HOST,setting.PORT))
        
        while True:
            self.request,self.addr = self.socket.accept()
            print('a new clinet form %s......'  % (self.addr,))
            try:
                self.handle()
            except Exception as e:
                print('Error with client',e)
                self.request.close()

    def handle(self):
        while True:
            raw_data = self.request.recv(self.MSG_SIZE)
            if not raw_data:  
                print('connection %s is lost .....' % (self.addr,))
                del self.request,self.addr
                break


            data = json.loads(raw_data.decode('utf-8'))
            
            action_type = data.get('action_type')
            if action_type:
                if hasattr(self,"_%s" % action_type):
                    func = getattr(self,"_%s" % action_type)
                    func(data)
            else:
                print('error command')

    def load_accounts(self):
        config_obj = configparser.ConfigParser()
        config_obj.read(setting.ACCOUNT_FILE)
        return config_obj

    def authenticate(self,username,password):
        if username in self.accounts:
            _password = self.accounts[username]['password']
            md5_obj = hashlib.md5()
            md5_obj.update(password.encode('utf-8'))
            md5_password = md5_obj.hexdigest()
            print(md5_password,_password)
            if md5_password == _password:
                self.user_obj = self.accounts[username]
                self.user_obj['home'] = os.path.join(setting.USER_HOME_DIR,username)
                self.user_current_dir = self.user_obj['home']
                return True
            else:
                return False
        else:
            return False

    def send_response(self,status_code,*args,**kwargs):
        data = kwargs
        data['status_code'] = status_code
        data['status_msg'] = self.STATUS_CODE[status_code]
        data['fill'] = ''
        bytes_data = json.dumps(data).encode('utf-8')
        #不足1024则填充到1024
        if len(bytes_data) < self.MSG_SIZE:
            data['fill'] = data['fill'].zfill(self.MSG_SIZE - len(bytes_data))
            bytes_data = json.dumps(data).encode('utf-8')
      
        self.request.send(bytes_data)


    def _auth(self,data):
        """用户认证"""
        if self.authenticate(data.get('username'),data.get('password')):
            self.send_response(status_code=200)
        else:
            self.send_response(status_code=201)


    def _get(self,data):
        """
        1. 拿到文件名
        2. 判断文件是否存在
            2.1 存在，返回状态码+文件大小
            2.2 不存在，返回状态码
        """
        filename = data.get('filename')
        full_path = os.path.join(self.user_obj['home'],filename)
        if os.path.isfile(full_path):
            filesize = os.stat(full_path).st_size
            self.send_response(301,file_size=filesize)
            print('ready to send file ')
            f = open(full_path,'rb')
            for line in f:
                self.request.send(line)
            else:
                print('file send done..')
            f.close
        else:
            self.send_response(300)
        

    def _ls(self,data):
        cmd_obj = subprocess.Popen('ls %s' %self.user_current_dir,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        stdout = cmd_obj.stdout.read()
        stderr = cmd_obj.stderr.read()

        cmd_result = stdout + stderr

        if not cmd_result:
            cmd_result = b'current dir has no file at all'

        self.send_response(302,cmd_result_size=len(cmd_result))
        self.request.sendall(cmd_result)


    def _put(self,data):
        """
        1. 拿到文件名，文件大小
        2. 检查是否存在这个文件
            2.1 存在则创建一个新的文件，以时间戳为后缀
            2.2 不存在则创建文件
        """

        local_file = data.get('filename')
        full_path = os.path.join(self.user_current_dir,local_file)
        if os.path.isfile(full_path):
            filename = '%s.%s' %(full_path,time.time())
        else:
            filename = full_path

        f = open(filename,'wb')
        total_size = data.get('file_size')
        received_size = 0

        while received_size < total_size:
            if total_size - received_size < 8192:
                data = self.request.recv(total_size - received_size)
            else:
                data = self.request.recv(8192)
            received_size += len(data)
            f.write(data)
            print(received_size,total_size)
        else:
            print('file %s recv done' % local_file)
            f.close()