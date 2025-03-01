import socket
from threading import Thread

'''
给服务器的命令：
①对话：“msg {name} {word}”
②注册：“reg {name}”
③退出：“exit”

从服务器得到的消息：
①对话：“msg {name} {word}”
②广播：“BC {list}”
③断连：“exit {reason}”
'''


class Client:
    def __init__(self):
        self.ip = "127.0.0.1"
        self.port = 0
        self.name = "Unknown"
        self.user_list = []
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def link_server(self):
        self.ip = input(">>输入你要链接的服务器的IP： ")
        self.port = int(input(">>输入你要链接的服务器的端口： "))
        try:
            self.client_socket.connect((self.ip, self.port))
            self.name = input(">>输入用户名：")
            reg_msg = "reg " + self.name
            self.client_socket.send(reg_msg.encode("utf-8"))    # 注册名字
            print(f">>连接成功，欢迎 {self.name}")
            user_list_msg = self.client_socket.recv(1024).decode("utf-8")   # 接收用户列表信息
            self.user_list = user_list_msg.split(",")
            print(f">>当前在线用户：{user_list_msg}")
            thread1 = Thread(target=self.recv_msg, args=(self.client_socket, ))
            thread1.start()
            self.send_msg(self.client_socket)

        except Exception as e:
            print(e)
            self.client_socket.close()
            return

    def send_msg(self, client: socket):
        while True:
            to_who = input("\n>>请选择私聊对象：")
            if to_who.lower() == "/exit":  # 退出
                client.send("exit".encode("utf-8"))
                client.close()
                print(f"\n>>再见， {self.name}")
                return
            if to_who not in self.user_list:
                print("\n>>当前对象不在线")
                continue
            while True:
                msg = input("\n>>请输入发送消息： ")
                if msg.lower() == "/exit":   # 退出
                    client.send("exit".encode("utf-8"))
                    client.close()
                    print(f"\n>>再见， {self.name}")
                    return
                if msg.lower() == "/msg":   # 切换私聊对象
                    break
                data = "msg" + " " + to_who + " " + msg
                client.send(data.encode("utf-8"))

    def recv_msg(self, client: socket):
        while True:
            data = client.recv(1024).decode("utf-8").split(" ")
            # print(data)
            command = data[0]
            if command == "exit":
                reason = data[1]
                print(f"\n>>服务器断开连接： {reason}")
                client.close()
                return
            elif command == "BC":
                msg = data[1]
                self.user_list = msg.split(",")
                print(f"\n>>更新当前在线用户：{msg}")
            else:
                name = data[1]
                msg = data[2]
                print(f"\n[{name}]: {msg}")


if __name__ == '__main__':
    client1 = Client()
    client1.link_server()
