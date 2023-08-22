import socket
import json
import configparser
import hashlib
from conf import setting

class FTPServer(object):
    def __init__(self,managent_instance):
        self.mangent_instance = managent_instance
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.socket.bind((setting.HOST,setting.PORT))
        self.socket.listen(setting.MAX_SOCKET_LISTEN)
        self.accounts = self.load_accounts()
        print(self.accounts)

    def run_forever(self):
        print('starting FTP server on %s:%s'.center(50,'-') % (setting.HOST,setting.PORT))

        self.request,self.addr = self.socket.accept()
        print('a new clinet form %s......'  % (self.addr,))

        self.handle()

    def handle(self):
        while True:
            raw_data = self.request.recv(1024)
            if not raw_data:
                continue
            # print('------',raw_data)
            
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
                print('success')
                return True
            else:
                print('wrong password')
                return False
        else:
            print('wrong username')
            return False


    def _auth(self,data):
        """用户认证"""
        if self.authenticate(data.get('username'),data.get('password')):
            print('pass auth')