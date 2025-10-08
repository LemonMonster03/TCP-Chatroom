import socket
from threading import Thread, Event
import signal
import sys
import time


class Client:
    def __init__(self):
        self.ip = "127.0.0.1"
        self.port = 0
        self.name = "Unknown"
        self.user_list = []
        self.client_socket = None
        # 同步信号
        self.stop_event = Event()
        self.current_chat = None
        self.connected = False

    def link_server(self):
        """连接服务器"""
        self.ip = input(">>输入服务器IP： ").strip()
        self.port = int(input(">>输入服务器端口： "))

        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.ip, self.port))
            self.name = input(">>输入用户名：").strip()

            if not self.name:
                print(">>用户名不能为空")
                return

            # 注册信息
            reg_msg = "reg " + self.name
            self.client_socket.send(reg_msg.encode("utf-8"))

            # 等待服务器响应
            self.client_socket.settimeout(5)
            response = self.client_socket.recv(1024).decode("utf-8").strip()
            self.client_socket.settimeout(None)

            if response.startswith("error"):
                error_msg = response.split(" ", 1)[1] if " " in response else "未知错误"
                print(f">>连接失败：{error_msg}")
                self.client_socket.close()
                return

            # 获取在线列表
            self.user_list = response.split(",") if response else []
            self.connected = True
            print(f">>连接成功，欢迎 {self.name}")
            print(f">>当前在线用户：{response}")

            # 注册 Ctrl+C 处理函数
            signal.signal(signal.SIGINT, self.signal_handler)

            # 启动消息接收线程
            recv_thread = Thread(target=self.recv_msg, daemon=True)
            recv_thread.start()

            # 主线程处理消息发送
            self.send_msg()

        except socket.timeout:
            print(">>连接超时")
        except Exception as e:
            print(f">>连接错误：{e}")
        finally:
            self.cleanup()

    def signal_handler(self, sig, frame):
        """处理 Ctrl+C 信号"""
        print("\n>>检测到退出信号，正在断开连接...")
        self.stop_event.set()
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        """清理资源"""
        if self.connected and self.client_socket:
            try:
                self.client_socket.send("exit".encode("utf-8"))
            except:
                pass

        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass

        self.connected = False

    def send_msg(self):
        """消息发送"""
        try:
            # 主循环： 未收到停止信号
            while not self.stop_event.is_set():
                # 选择聊天对象
                if not self.current_chat:
                    try:
                        to_who = input("\n>>请选择私聊对象（/exit 退出，/list 查看在线用户）：").strip()
                    except EOFError:
                        break
                    # 指令检测
                    if to_who.lower() == "/exit":
                        break

                    if to_who.lower() == "/list":
                        print(f">>当前在线用户：{','.join(self.user_list)}")
                        continue

                    if to_who not in self.user_list:
                        print(f">>用户 {to_who} 当前不在线")
                        continue

                    self.current_chat = to_who
                    print(f">>已切换到与 {to_who} 的对话（/exit 退出，/back 切换对象）")

                # 已选择对象，发送消息
                try:
                    msg = input(f"[发往 {self.current_chat}] >>> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break

                # 指令检测
                if msg.lower() == "/exit":
                    break

                if msg.lower() == "/back":
                    self.current_chat = None
                    continue

                if msg:
                    try:
                        data = f"msg {self.current_chat} {msg}"
                        self.client_socket.send(data.encode("utf-8"))
                    except Exception as e:
                        print(f">>发送失败：{e}")
                        break

        except Exception as e:
            if not self.stop_event.is_set():
                print(f">>发送消息时出错：{e}")
        finally:
            print(f"\n>>再见，{self.name}")
            # 使接收线程也同步退出
            self.stop_event.set()

    def recv_msg(self):
        """消息接收"""
        while not self.stop_event.is_set():
            try:
                data = self.client_socket.recv(1024).decode("utf-8").strip()

                # 空串：表示服务器断联
                if not data:
                    print("\n>>服务器断开连接")
                    self.stop_event.set()
                    break

                msg_parts = data.split(" ", 2)
                command = msg_parts[0]

                # 指令检测
                if command == "exit":
                    reason = msg_parts[1] if len(msg_parts) > 1 else "未知原因"
                    print(f"\n>>服务器断开连接：{reason}")
                    self.stop_event.set()
                    break
                elif command == "BC":
                    # 更新用户列表
                    if len(msg_parts) > 1:
                        self.user_list = msg_parts[1].split(",") if msg_parts[1] else []
                        # 检查当前聊天对象是否还在线
                        if self.current_chat and self.current_chat not in self.user_list:
                            print(f"\n>>【提示】聊天对象 {self.current_chat} 已下线")
                            self.current_chat = None

                        print(f"\n>>在线用户更新：{msg_parts[1]}")

                        # 重新显示输入提示符>>>
                        if self.current_chat:
                            print(f"[发往 {self.current_chat}] >>> ", end='', flush=True)
                        else:
                            print(">>请选择私聊对象：", end='', flush=True)

                elif command == "msg":
                    if len(msg_parts) >= 3:
                        sender = msg_parts[1]
                        content = msg_parts[2]
                        print(f"\n[{sender}]：{content}")

                        # 重新显示输入提示符>>>
                        if self.current_chat:
                            print(f"[→ {self.current_chat}] >>> ", end='', flush=True)
                        else:
                            print(">>请选择私聊对象：", end='', flush=True)
            except Exception as e:
                if not self.stop_event.is_set():
                    print(f"\n>>接收消息时出错：{e}")
                self.stop_event.set()
                break


if __name__ == '__main__':
    client = Client()
    client.link_server()
