import optparse
import socket
import json
import os


class Client(object):
    
    MSG_SIZE = 1024 #消息最常1024

    def __init__(self):
        self.username = None
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


    def get_response(self):
        """获取服务端返回的数据"""
        data = self.socket.recv(self.MSG_SIZE)
        return json.loads(data.decode())


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
            response = self.get_response()
            if response.get('status_code') == 200:
                self.username = username
                return True
            else:
                print(response.get('status_msg'))
                count += 1

    def interactive(self):
        """处理交互"""
        if self.auth():
            while True:
                user_input = input('[%s]>>:'%self.username).strip()
                if not user_input:continue

                cmd_list = user_input.split()
                if hasattr(self,"_%s" % cmd_list[0]):
                    func = getattr(self,'_%s' % cmd_list[0])
                    func(cmd_list[1:])

    def parameter_ckeck(self,args,min_args=None,max_args = None,exact_args = None):
        if min_args:
            if len(args) < min_args:
                print('must provide at least %s parameters but %s received' %(min_args,len(args)))
                return False

        if max_args:
            if len(args) > max_args:
                print('need at most %s parameters but %s received' %(max_args,len(args)))
                return False
            
        if exact_args:
            if len(args) != exact_args:
                print('need exactly %s parameters but %s received' %(exact_args,len(args)))
                return False

        return True
    

    def send_msg(self,action_type,**kwargs):
        msg_data = {
            'action_type':action_type,
            'fill':''
        }
        #合并字典
        msg_data.update(kwargs)
        bytes_msg = json.dumps(msg_data).encode()
        if len(bytes_msg) < self.MSG_SIZE:
             msg_data['fill'] = msg_data['fill'].zfill(self.MSG_SIZE - len(bytes_msg))
             byte_msg = json.dumps(msg_data).encode()


        self.socket.send(byte_msg)

    def _get(self,cmd_args):
        """
        1. 拿到用户名
        2. 发送到服务器
        3. 等待服务器返回消息
            3.1 如果文件存在，拿到文件大小
                3.1.1 循环接收
            3.2 文件不存在，输出错误消息
        """
        if self.parameter_ckeck(cmd_args,min_args=1):
            filename = cmd_args[0]
            self.send_msg(action_type='get',filename=filename)
            response = self.get_response()
            if response.get('status_code') == 301:
                file_size = response.get('file_size')

                received_size = 0
                f = open(filename,'wb')
                while received_size < file_size:
                    if file_size - received_size < 8192:    #最后一次接收
                        data = self.socket.recv(file_size - received_size)
                    else:
                        data = self.socket.recv(8192)
                    received_size += len(data)
                    f.write(data)
                else:
                    print('---file [%s]----size [%s] downloads success' % (filename,file_size))
                    f.close()
            else:
                print(response.get('status_msg'))

    def _ls(self,cmd_args):
        self.send_msg(action_type='ls')
        response = self.get_response()
        # print(response)
        if response.get('status_code') == 302:
            cmd_result_size = response.get('cmd_result_size')
            
            received_size = 0
            cmd_result = b''
            while received_size < cmd_result_size:
                if cmd_result_size - received_size < 8192:
                    data = self.socket.recv(cmd_result_size - received_size)
                else:
                    data = self.socket.recv(8192)
                cmd_result += data
                received_size += len(data)
            else:
                print(cmd_result)


    def progress_bar(self,total_size):
        current_percent = 0
        last_percent = 0
        while True:
            received_size = yield current_percent
            current_percent = int(received_size / total_size * 100)
            
            if current_percent > last_percent:
                print('#'*current_percent + "{percent}%s".format(percent= current_percent),end='\r',flush=True)
                last_percent = current_percent

    def _put(self,cmd_args):
        """
        1. 确保本地文件存在
        2. 获取文件名+文件大小，放到消息头发给服务器
        3. 打开文件，发送内容
        """
        if self.parameter_ckeck(cmd_args,exact_args=1):
            local_file = cmd_args[0]
            if os.path.isfile(local_file):
                total_size = os.path.getsize(local_file)
                self.send_msg('put',file_size=total_size,filename=local_file)
                f = open(local_file,'rb')
                uploaded_size = 0. #已经上传的大小
                
                progress_generator = self.progress_bar(total_size)
                progress_generator.__next__()
                # last_percent = 0
                for line in f:
                    self.socket.send(line)
                    uploaded_size += len(line)
                    # current_percent = int(uploaded_size / total_size * 100)
                    # if current_percent > last_percent:
                    #     print('#'*current_percent + "{percent}%s".format(percent=current_percent),end='\r',flush=True)
                    #     last_percent = current_percent
                    progress_generator.send(uploaded_size)
                else:
                    print('file upload done'.center(50,'-'))
                    f.close()

if __name__ == "__main__":
    client = Client()