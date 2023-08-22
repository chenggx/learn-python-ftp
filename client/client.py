import optparse
import socket
import json


class Client(object):

    def __init__(self):
        
        parser = optparse.OptionParser()
        parser.add_option('-s','--server',dest='server',help='ftp server ip_adder')
        parser.add_option('-P','--port',type='int',dest='port',help='ftp server port')
        parser.add_option('-u','--username',dest='username',help='ftp server username')
        parser.add_option('-p','--password',dest='password',help='ftp server password')
        self.options,self.args = parser.parse_args()

        self.argv_verification()

        self.connection()

        

    def argv_verification(self):
        """检查参数合法性"""
        if not self.options.server or not self.options.port:
            exit('参数有误')


    def connection(self):
        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.socket.connect((self.options.server,self.options.port))
        self.interactive()


    def auth(self):
        
        count = 0
        while count < 3:
            username = input('username:').strip()
            if not username:continue
            password = input('passowrd:').strip()
            cmd = {
                'action_type':'auth',
                'username':username,
                'password':password
            }

            self.socket.send(json.dumps(cmd).encode('utf-8'))
            self.socket.recv(1024)

    def interactive(self):
        """处理交互"""
        if self.auth():
            pass


if __name__ == "__main__":
    client = Client()