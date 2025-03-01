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

IP = "172.26.76.125"    # 请自行更改

class Server:
    def __init__(self):
        self.user_name = []
        self.user_list = []
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self):

        port = int(input(">>请输入端口:"))
        try:
            self.server_socket.bind((IP, port))
            print(f">>服务器成功在{port}上启动")
            cnt = int(input(">>请输入监听数量："))
            if cnt <= 0:
                raise Exception("至少要有1个监听数量！目前是：", cnt)
            self.server_socket.listen(cnt)
            print(f">>服务器正在监听")
            while True:
                client_socket, addr = self.server_socket.accept()
                thread = Thread(target=self.handle, args=(client_socket, addr))
                thread.start()
        except Exception as e:
            print(e)
            self.server_socket.close()
            return

    def handle(self, client, addr):
        print(f">>收到来自{addr}的连接")
        data = client.recv(1024).decode("utf-8").split(" ")
        if data[0] != "reg":
            print(">>ERROR")
            client.close()
            return
        name = data[1]
        self.user_name.append(name)
        # print("test1: ", self.user_name)
        self.user_list.append(client)
        user_list = ""
        for p in self.user_name:
            user_list += (p + ",")

        self.broadcast(client)  # 通知所有人新用户登入
        client.send(user_list.encode("utf-8"))  # 发送用户列表

        try:
            while True:
                msg = client.recv(1024).decode("utf-8").split(" ")
                if not msg:
                    raise Exception("lost connection")
                if msg[0] == "exit":
                    print(f">>{name} 退出连接")
                    self.user_name.remove(name)
                    self.user_list.remove(client)
                    user_list = ""
                    for p in self.user_name:
                        user_list += (p + " ")
                    for c in self.user_list:
                        if c != client:
                            c.send(("msg " + "Server " + f"用户'{name}'登出！").encode("utf-8"))
                            c.send(("BC " + user_list).encode("utf-8"))
                    client.close()
                elif msg[0] == "msg":
                    dst_name = msg[1]
                    if dst_name not in self.user_name:
                        client.send(("msg " + "Server " + f"用户'{dst_name}'已经离线！").encode("utf-8"))
                    else:
                        content = msg[2]
                        dst_client = self.user_list[self.user_name.index(dst_name)]
                        dst_client.send(("msg " + name + " " + content).encode("utf-8"))
        except Exception as e:
            print(e)
            print(">>一个链接已断开")
            # self.user_name.remove(name)
            # self.user_list.remove(client)
            user_list = ""
            for p in self.user_name:
                user_list += (p + " ")
            for c in self.user_list:
                if c != client:
                    c.send(("msg " + "Server " + f"用户'{name}'登出！").encode("utf-8"))
                    c.send(("BC " + user_list).encode("utf-8"))
            client.close()
            return

    def broadcast(self, new_client):
        name = self.user_name[self.user_list.index(new_client)]
        user_list = ""
        for p in self.user_name:
            user_list += (p + ",")
        # print("test2: ", user_list)
        for client in self.user_list:
            if client != new_client:
                client.send(("msg " + "Server " + f"用户'{name}'登入！").encode("utf-8"))
        for client in self.user_list:
            if client != new_client:
                client.send(("BC " + user_list).encode("utf-8"))


if __name__ == '__main__':
    server = Server()
    server.start()