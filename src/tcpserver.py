import socket
from threading import Thread, Lock

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


IP = "127.0.0.1"


class Server:
    def __init__(self):
        self.user_name = []
        self.user_list = []
        # IPV4 TCP
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lock = Lock()

    def start(self):
        """启动服务器"""
        port = int(input(">>请输入端口:"))
        try:
            # 允许地址复用
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((IP, port))
            print(f">>服务器成功在{port}上启动")
            cnt = int(input(">>请输入监听数量："))
            if cnt <= 0:
                raise Exception("至少要有1个监听数量！目前是：", cnt)
            # 监听
            self.server_socket.listen(cnt)
            print(f">>服务器正在监听")
            # 分派线程处理
            while True:
                client_socket, addr = self.server_socket.accept()
                thread = Thread(target=self.handle, args=(client_socket, addr))
                # 守护线程，避免阻塞
                thread.daemon = True
                thread.start()
        except Exception as e:
            print(f">>服务器错误：{e}")
            self.server_socket.close()
            return

    def handle(self, client, addr):
        """处理客户端链接"""
        name = None
        registered = False
        print(f">>收到来自{addr}的连接")

        try:
            """注册处理"""
            # 接收注册消息（设置超时防止卡死）
            client.settimeout(10)
            data = client.recv(1024).decode("utf-8").strip()
            client.settimeout(None)  # 取消超时

            # 检验请求
            if not data:
                print(">>ERROR: 空注册请求")
                client.close()
                return

            msg_parts = data.split(" ", 1)
            if msg_parts[0] != "reg" or len(msg_parts) < 2:
                print(">>ERROR: 无效的注册请求")
                client.send(("error 无效的注册格式").encode("utf-8"))
                client.close()
                return

            name = msg_parts[1].strip()

            if not name:
                print(">>ERROR: 用户名为空")
                client.send(("error 用户名不能为空").encode("utf-8"))
                client.close()
                return

            # 检查用户名是否已存在
            with self.lock:
                if name in self.user_name:
                    print(f">>ERROR: 用户名 {name} 已存在")
                    client.send(("error 用户名已存在").encode("utf-8"))
                    client.close()
                    return

                self.user_name.append(name)
                self.user_list.append(client)
                registered = True
                user_list = ",".join(self.user_name)

            print(f">>{name} 成功注册，当前在线用户：{user_list}")

            # 发送当前在线用户列表给新用户
            client.send(user_list.encode("utf-8"))

            # 广播新用户
            self.broadcast_join(name, client)

            """转发消息"""
            # 主循环
            while True:
                msg = client.recv(1024).decode("utf-8").strip()

                if not msg:
                    print(f">>{name} 发送空消息")
                    raise ConnectionResetError("客户端发送空消息")

                msg_parts = msg.split(" ", 2)
                command = msg_parts[0]

                # 指令处理
                if command == "exit":
                    print(f">>{name} 主动退出连接")
                    break
                elif command == "msg":
                    if len(msg_parts) < 3:
                        continue
                    recv_name = msg_parts[1]
                    content = msg_parts[2]

                    with self.lock:
                        if recv_name not in self.user_name:
                            try:
                                client.send(("msg Server " + f"用户'{recv_name}'已经离线！").encode("utf-8"))
                            except:
                                break
                        else:
                            idx = self.user_name.index(recv_name)
                            recv_client = self.user_list[idx]
                            try:
                                recv_client.send(("msg " + name + " " + content).encode("utf-8"))
                            except:
                                print(f">>发送消息到 {recv_name} 失败")
        # 异常处理
        except socket.timeout:
            print(f">>客户端 {name or addr} 注册超时")
        except Exception as e:
            print(f">>客户端 {name or 'Unknown'} 发生错误：{e}")
        # 清理资源
        finally:
            if name and registered:
                cleanup_success = False
                with self.lock:
                    try:
                        if name in self.user_name:
                            idx = self.user_name.index(name)
                            self.user_name.pop(idx)
                            self.user_list.pop(idx)
                            cleanup_success = True
                            print(f">>{name} 已从用户列表中移除，当前在线：{','.join(self.user_name)}")
                    except (ValueError, IndexError) as e:
                        print(f">>清理用户 {name} 时出错：{e}")

                # 在锁外广播（避免死锁）
                if cleanup_success:
                    self.broadcast_exit(name)
            try:
                client.close()
            except:
                pass

    def broadcast_join(self, name, new_client):
        """广播新用户加入"""
        with self.lock:
            user_list = ",".join(self.user_name)
            clients = [c for c in self.user_list if c != new_client]

        for client in clients:
            try:
                client.send(("msg Server " + f"用户'{name}'登入！").encode("utf-8"))
                client.send(("BC " + user_list).encode("utf-8"))
            except Exception as e:
                print(f">>广播加入消息失败：{e}")

    def broadcast_exit(self, name):
        """广播用户退出"""
        with self.lock:
            user_list = ",".join(self.user_name)
            clients = list(self.user_list)

        for client in clients:
            try:
                client.send(("msg Server " + f"用户'{name}'登出！").encode("utf-8"))
                client.send(("BC " + user_list).encode("utf-8"))
            except Exception as e:
                print(f">>广播退出消息失败：{e}")


if __name__ == '__main__':
    server = Server()
    server.start()
