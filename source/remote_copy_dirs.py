#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import paramiko
import os
import re
from datetime import datetime
from scp import SCPClient
import sys
import time

class SSHCopierWithRetry:
    def __init__(self, host, port, username, password, max_retries=3):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.max_retries = max_retries
        self.ssh = None
        self.scp = None
        
    def connect(self):
        """建立SSH连接，支持重试"""
        for attempt in range(self.max_retries):
            try:
                self.ssh = paramiko.SSHClient()
                self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.ssh.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    password=self.password,
                    timeout=30
                )
                self.scp = SCPClient(self.ssh.get_transport())
                print(f"成功连接到 {self.host}:{self.port}")
                return True
            except Exception as e:
                if attempt < self.max_retries - 1:
                    print(f"连接尝试 {attempt+1}/{self.max_retries} 失败: {e}")
                    time.sleep(5)  # 等待5秒后重试
                else:
                    print(f"连接失败: {e}")
                    return False
                    
    def disconnect(self):
        """关闭连接"""
        if self.scp:
            self.scp.close()
        if self.ssh:
            self.ssh.close()
        print("连接已关闭")
        
    def get_recent_date_dirs(self, remote_path, days=30):
        """获取远程目录中最近days天的日期子目录"""
        try:
            stdin, stdout, stderr = self.ssh.exec_command(f'ls {remote_path}')
            dirs = stdout.read().decode().splitlines()
            stderr.read()  # 清空错误输出
            
            # 过滤出日期格式的目录 (8位数字)
            date_dirs = []
            for d in dirs:
                if re.match(r'^\d{8}$', d):
                    try:
                        date = datetime.strptime(d, '%Y%m%d')
                        date_dirs.append((d, date))
                    except ValueError:
                        continue
            
            # 按日期排序并获取最近的
            date_dirs.sort(key=lambda x: x[1], reverse=True)
            recent_dirs = [d[0] for d in date_dirs[:days]]
            
            print(f"找到 {len(recent_dirs)} 个最近 {days} 天的目录")
            return recent_dirs
            
        except Exception as e:
            print(f"获取目录列表失败: {e}")
            return []
            
    def copy_directory_with_retry(self, remote_base_path, local_base_path, dir_name, skip_existing=True, max_retries=3):
        """复制单个目录，支持重试"""
        remote_dir = f"{remote_base_path}/{dir_name}"
        local_dir = f"{local_base_path}/{dir_name}"
        
        # 检查本地目录是否已存在
        if skip_existing and os.path.exists(local_dir):
            print(f"跳过已存在的目录: {dir_name}")
            return True
            
        for attempt in range(max_retries):
            try:
                # 创建本地目录
                os.makedirs(local_dir, exist_ok=True)
                
                # 使用SCP复制整个目录
                self.scp.get(remote_dir, local_path=local_base_path, recursive=True)
                print(f"成功复制: {dir_name}")
                return True
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"复制目录 {dir_name} 尝试 {attempt+1}/{max_retries} 失败: {e}")
                    time.sleep(10)  # 等待10秒后重试
                else:
                    print(f"复制目录 {dir_name} 失败: {e}")
                    return False
            
    def copy_recent_directories(self, remote_path, local_path, days=30, skip_existing=True):
        """复制最近days天的目录"""
        if not self.ssh:
            print("请先建立SSH连接")
            return False
        # 确保本地目录存在
        os.makedirs(local_path, exist_ok=True)

        
        # 获取最近日期的目录
        recent_dirs = self.get_recent_date_dirs(remote_path, days)
        
        if not recent_dirs:
            print("未找到符合条件的目录")
            return False
        
        # 复制每个目录
        success_count = 0
        for dir_name in recent_dirs:
            if self.copy_directory_with_retry(remote_path, local_path, dir_name, skip_existing):
                success_count += 1
        
        print(f"复制完成: 成功 {success_count}/{len(recent_dirs)} 个目录")
        return success_count > 0

def main():
    # 配置参数 - 请修改这些值
    HOST = "192.168.1.107"
    PORT = 22
    USERNAME = "root"  # 替换为你的用户名
    PASSWORD = "000416bb"  # 替换为你的密码
    
    REMOTE_PATH = "/common/data_3s_feather_full"
    LOCAL_PATH = "/home/ubuntu/common"
    DAYS = 30
    SKIP_EXISTING = True
    MAX_RETRIES = 3
    
    # 创建复制器实例
    copier = SSHCopierWithRetry(
        host=HOST,
        port=PORT,
        username=USERNAME,
        password=PASSWORD,
        max_retries=MAX_RETRIES
    )
    
    try:
        # 连接并复制
        if copier.connect():
            copier.copy_recent_directories(REMOTE_PATH, LOCAL_PATH, DAYS, SKIP_EXISTING)
        else:
            print("无法建立连接，请检查网络和凭据")
            
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"执行过程中发生错误: {e}")
        
    finally:
        # 确保连接关闭
        copier.disconnect()

if __name__ == "__main__":
    # 检查依赖
    try:
        import paramiko
        from scp import SCPClient
    except ImportError:
        print("请先安装所需依赖: pip install paramiko scp")
        sys.exit(1)
        
    main()