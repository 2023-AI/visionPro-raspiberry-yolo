#!/usr/bin/env python3
"""
Yahboom DOFBOT 手势控制TCP服务器（地面夹取优化版 + 独立舵机控制）
✅ 手臂下弯可碰到地面
✅ 新增一键到夹取位置
✅ 保留所有原有功能
✅ 新增2-6号舵机独立前倾/后仰控制（适配Vision Pro）
✅ 修复端口占用报错
✅ 修复树莓派真实IP获取错误
✅ 【新增】滑动摇杆绝对角度控制（S2:90 格式）
✅ 清理全部冗余重复代码，优化复位/舵机写入逻辑
"""

import socket
import time
from Arm_Lib import Arm_Device

# ====================== 安全角度范围 ======================
SAFE_LIMITS = {
    1: (0, 180),      # 底座
    2: (30, 165),     # 大臂（向下弯更大行程）
    3: (20, 150),     # 小臂
    4: (0, 180),      # 手腕
    5: (0, 270),      # 夹爪旋转
    6: (30, 150)      # 夹爪
}

# 标准垂直复位位置
RESET_POSITION = [90, 90, 90, 90, 90, 30]
# 地面夹取最优角度
PICK_POSITION = [90, 160, 25, 90, 90, 30]

# ====================== 机械臂控制类 ======================
class DofbotGestureController:
    def __init__(self):
        self.arm = Arm_Device()
        print("✅ Yahboom DOFBOT 机械臂初始化成功")
        self.current_angles = RESET_POSITION.copy()
        self.running = True
        print("🔄 正在强制复位到标准垂直位置...")
        self.force_reset()
        print("✅ 复位完成，所有关节已与地面垂直")

    def _clamp_angle(self, servo_id, angle):
        """限制舵机角度在安全区间"""
        min_a, max_a = SAFE_LIMITS[servo_id]
        return max(min_a, min(max_a, int(angle)))

    def _write_servo_angle(self, servo_id, angle, duration=500):
        """单次写入舵机角度，移除重复发送冗余"""
        angle = self._clamp_angle(servo_id, angle)
        try:
            self.arm.Arm_serial_servo_write(servo_id, angle, duration)
            time.sleep(duration / 1000 + 0.1)
            self.current_angles[servo_id - 1] = angle
            return True
        except Exception as e:
            print(f"❌ 舵机{servo_id}写入失败: {e}")
            return False

    def adjust_single_servo(self, servo_id, step):
        """单舵机步进微调 +5/-5"""
        new_angle = self.current_angles[servo_id - 1] + step
        if self._write_servo_angle(servo_id, new_angle, 300):
            return f"舵机{servo_id} → {new_angle}° ({step:+d}°)"
        return f"❌ 舵机{servo_id}调整失败"

    def set_servo_absolute(self, servo_id, angle):
        """滑块绝对角度控制 Sx:xxx"""
        angle = self._clamp_angle(servo_id, angle)
        if self._write_servo_angle(servo_id, angle, 300):
            return f"✅ 舵机{servo_id} 绝对角度 → {angle}°"
        return f"❌ 舵机{servo_id} 绝对角度设置失败"

    def force_reset(self):
        """精简复位逻辑，移除多次重复批量写入冗余"""
        self.arm.Arm_serial_servo_write6_array(RESET_POSITION, 1000)
        time.sleep(1.2)
        self.current_angles = RESET_POSITION.copy()
        return "✅ 机械臂已成功复位"

    # 底座旋转
    def base_left(self, step=10):
        new_angle = self._clamp_angle(1, self.current_angles[0] - step)
        if self._write_servo_angle(1, new_angle, 300):
            return f"底座左转 → {new_angle}°"
        return "底座左转失败"

    def base_right(self, step=10):
        new_angle = self._clamp_angle(1, self.current_angles[0] + step)
        if self._write_servo_angle(1, new_angle, 300):
            return f"底座右转 → {new_angle}°"
        return "底座右转失败"

    # 大臂小臂联动升降
    def arm_up(self, step=20):
        shoulder = self._clamp_angle(2, self.current_angles[1] - step)
        elbow = self._clamp_angle(3, self.current_angles[2] + step)
        s1 = self._write_servo_angle(2, shoulder, 500)
        s2 = self._write_servo_angle(3, elbow, 500)
        if s1 and s2:
            return f"手臂抬起 → 大臂{shoulder}° 小臂{elbow}°"
        return "手臂抬起失败"

    def arm_down(self, step=20):
        shoulder = self._clamp_angle(2, self.current_angles[1] + step)
        elbow = self._clamp_angle(3, self.current_angles[2] - step)
        s1 = self._write_servo_angle(2, shoulder, 500)
        s2 = self._write_servo_angle(3, elbow, 500)
        if s1 and s2:
            return f"手臂下弯 → 大臂{shoulder}° 小臂{elbow}°"
        return "手臂下弯失败"

    def go_to_pick_position(self):
        """一键到达地面夹取位，删除手动同步current_angles冗余"""
        print("🔄 正在移动到地面夹取位置...")
        self._write_servo_angle(6, SAFE_LIMITS[6][0], 300)
        time.sleep(0.3)
        self._write_servo_angle(2, PICK_POSITION[1], 800)
        self._write_servo_angle(3, PICK_POSITION[2], 800)
        time.sleep(1.0)
        self._write_servo_angle(4, PICK_POSITION[3], 300)
        time.sleep(0.3)
        return "✅ 已到达地面夹取位置"

    # 夹爪开关
    def gripper_open(self):
        if self._write_servo_angle(6, SAFE_LIMITS[6][0], 300):
            return "✅ 夹爪已张开"
        return "夹爪张开失败"

    def gripper_close(self):
        if self._write_servo_angle(6, SAFE_LIMITS[6][1], 300):
            return "✅ 夹爪已闭合"
        return "夹爪闭合失败"

    def process_command(self, command):
        command = command.strip().upper()
        print(f"\n收到指令: {command}")
        try:
            # 绝对角度指令 Sx:120
            if ":" in command:
                parts = command.split(":")
                if len(parts) != 2 or not parts[0].startswith("S"):
                    return "❌ 绝对角度格式错误，示例 S2:90"
                servo_id = int(parts[0][1:])
                angle = int(parts[1])
                if not 1 <= servo_id <= 6:
                    return "❌ 舵机编号必须 1~6"
                return self.set_servo_absolute(servo_id, angle)

            # 基础全局指令
            match command:
                case "BASE_LEFT": return self.base_left()
                case "BASE_RIGHT": return self.base_right()
                case "ARM_UP": return self.arm_up()
                case "ARM_DOWN": return self.arm_down()
                case "GRIPPER_OPEN": return self.gripper_open()
                case "GRIPPER_CLOSE": return self.gripper_close()
                case "RESET": return self.force_reset()
                case "PICK_POSITION": return self.go_to_pick_position()
                case "STATUS":
                    angle_text = [f"{i+1}:{a}°" for i, a in enumerate(self.current_angles)]
                    return f"当前角度: {', '.join(angle_text)}"
                # 单舵机步进 Sx+ Sx-
                case "S1+": return self.adjust_single_servo(1, 5)
                case "S1-": return self.adjust_single_servo(1, -5)
                case "S2+": return self.adjust_single_servo(2, 5)
                case "S2-": return self.adjust_single_servo(2, -5)
                case "S3+": return self.adjust_single_servo(3, 5)
                case "S3-": return self.adjust_single_servo(3, -5)
                case "S4+": return self.adjust_single_servo(4, 5)
                case "S4-": return self.adjust_single_servo(4, -5)
                case "S5+": return self.adjust_single_servo(5, 5)
                case "S5-": return self.adjust_single_servo(5, -5)
                case "S6+": return self.adjust_single_servo(6, 5)
                case "S6-": return self.adjust_single_servo(6, -5)
                case _: return f"❌ 未知指令: {command}"
        except ValueError:
            return "❌ 指令参数必须为数字"
        except Exception as e:
            return f"❌ 执行错误: {str(e)}"

    def shutdown(self):
        print("\n🔄 正在安全关闭...")
        self.running = False
        self.force_reset()
        print("✅ 已安全关闭，机械臂已复位")

# 获取本机WiFi局域网IP
def get_real_wifi_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# TCP服务主逻辑
def main():
    controller = None
    server_socket = None
    try:
        controller = DofbotGestureController()
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 解决端口复用占用
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        server_socket.settimeout(1.0)

        HOST = "0.0.0.0"
        PORT = 9500
        server_socket.bind((HOST, PORT))
        server_socket.listen(1)

        print(f"\n✅ TCP服务器已启动")
        print(f"监听地址: {HOST}:{PORT}")
        print(f"🌐 树莓派真实WiFi IP: {get_real_wifi_ip()}")
        print("💡 PICK_POSITION 一键夹取地面")
        print("💡 绝对角度指令格式 S舵机号:角度 例 S2:90")
        print("等待Apple Vision Pro连接...")

        while True:
            try:
                client_socket, client_addr = server_socket.accept()
                print(f"\n✅ 客户端已连接: {client_addr}")
                try:
                    while True:
                        data = client_socket.recv(1024)
                        if not data:
                            break
                        resp = controller.process_command(data.decode("utf-8"))
                        print(f"执行结果: {resp}")
                        client_socket.sendall(resp.encode("utf-8"))
                except Exception as e:
                    print(f"客户端通讯异常: {str(e)}")
                finally:
                    client_socket.close()
                    print("客户端已断开连接")
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        print("\n\n程序被用户Ctrl+C中断")
    finally:
        if server_socket:
            server_socket.close()
        if controller:
            controller.shutdown()

if __name__ == "__main__":
    main()
