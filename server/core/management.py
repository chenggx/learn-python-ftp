from core import main

class ManagementTool(object):
    """解析指令 """
    def __init__(self,sys_argv):
        self.sys_argv = sys_argv
        self.verify_argv()
        
    def verify_argv(self):
        """验证指令是否合法"""
        if len(self.sys_argv) < 2:
            self.help_msg()
        cmd = self.sys_argv[1]
        #通过反射判断当前类中是否有cmd方法
        if not hasattr(self,cmd):
            print('invalid argument!')
            self.help_msg()
        self.execute()

    def help_msg(self):
        msg = '''
            start start FPT server
            stop stop FPT server
            restart restart FPT server
'''
        exit(msg)


    def execute(self):
        """执行指令"""
        cmd = self.sys_argv[1]
        func = getattr(self,cmd)
        func()


    def start(self):
        server = main.FTPServer(self)
        server.run_forever()