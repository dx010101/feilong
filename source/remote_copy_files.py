#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import paramiko
import os
from datetime import datetime
import sys
import time

class SSHFileCopier:
    def __init__(self, host, port, username, password, max_retries=3):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.max_retries = max_retries
        self.ssh = None
        self.sftp = None
        
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
                self.sftp = self.ssh.open_sftp()
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
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
        print("连接已关闭")
        
    def get_recent_files(self, remote_path, file_count=30):
        """获取远程目录中最新的file_count个文件"""
        try:
            # 列出远程目录中的所有文件
            files = self.sftp.listdir(remote_path)
            
            # 过滤出符合日期格式的文件 (YYYYMMDD.xxx)
            date_files = []
            for f in files:
                # 使用split方法提取日期部分
                if '.' in f:
                    date_part = f.split('.')[0]
                    
                    # 检查是否为8位数字
                    if len(date_part) == 8 and date_part.isdigit():
                        try:
                            date = datetime.strptime(date_part, '%Y%m%d')
                            date_files.append((f, date))
                        except ValueError:
                            # 日期格式无效，跳过
                            continue
            
            # 按日期排序并获取最新的文件
            date_files.sort(key=lambda x: x[1], reverse=True)
            recent_files = [f[0] for f in date_files[:file_count]]
            
            print(f"找到 {len(recent_files)} 个最新的文件")
            if recent_files:
                print("最新的文件:", recent_files[0])
                if len(recent_files) > 1:
                    print("最旧的文件:", recent_files[-1])
            return recent_files
            
        except Exception as e:
            print(f"获取文件列表失败: {e}")
            return []
            
    def copy_file_with_retry(self, remote_path, local_path, file_name, skip_existing=True, max_retries=3):
        """复制单个文件，支持重试"""
        remote_file = f"{remote_path}/{file_name}"
        local_file = f"{local_path}/{file_name}"
        
        # 检查本地文件是否已存在
        if skip_existing and os.path.exists(local_file):
            print(f"跳过已存在的文件: {file_name}")
            return True
            
        for attempt in range(max_retries):
            try:
                # 确保本地目录存在
                os.makedirs(local_path, exist_ok=True)
                print(f"正在复制从: {remote_file} 至 {local_file}")
                # 使用SFTP复制文件
                self.sftp.get(remote_file, local_file)
                
                # 验证文件是否成功复制
                if os.path.exists(local_file) and os.path.getsize(local_file) > 0:
                    print(f"成功复制: {file_name} ({os.path.getsize(local_file)} 字节)")
                    return True
                else:
                    raise Exception("复制后文件为空或不存在")
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"复制文件 {file_name} 尝试 {attempt+1}/{max_retries} 失败: {e}")
                    time.sleep(10)  # 等待10秒后重试
                    
                    # 删除可能损坏的部分文件
                    if os.path.exists(local_file):
                        try:
                            os.remove(local_file)
                        except:
                            pass
                else:
                    print(f"复制文件 {file_name} 失败: {e}")
                    return False
            
    def copy_recent_files(self, remote_path, local_path, file_count=30, skip_existing=True):
        """复制最新的file_count个文件"""
        if not self.ssh:
            print("请先建立SSH连接")
            return False
            
        # 确保本地目录存在
        os.makedirs(local_path, exist_ok=True)
        
        # 获取最新的文件
        recent_files = self.get_recent_files(remote_path, file_count)
        
        if not recent_files:
            print("未找到符合条件的文件")
            return False
        
        print(f"开始复制 {len(recent_files)} 个文件...")
        
        # 复制每个文件
        success_count = 0
        for file_name in recent_files:
            if self.copy_file_with_retry(remote_path, local_path, file_name, skip_existing):
                success_count += 1
        
        print(f"复制完成: 成功 {success_count}/{len(recent_files)} 个文件")
        return success_count > 0

def main():
    # 配置参数 - 请修改这些值
    HOST = "192.168.1.107"
    PORT = 22
    USERNAME = "root"  # 替换为你的用户名
    PASSWORD = "000416bb"  # 替换为你的密码
    
    REMOTE_PATH = "/common/data_triggers/max_15s_turnover/xdata_cpp"  # 替换为你的远程路径
    LOCAL_PATH = "/common/data_triggers/max_15s_turnover/xdata_cpp"  # 替换为你的本地路径
    if not os.path.exists(LOCAL_PATH):
        os.makedirs(LOCAL_PATH)
    FILE_COUNT = 10000  # 要复制的最新文件数量
    SKIP_EXISTING = True  # 是否跳过已存在的文件
    MAX_RETRIES = 3  # 最大重试次数
    
    # 创建复制器实例
    copier = SSHFileCopier(
        host=HOST,
        port=PORT,
        username=USERNAME,
        password=PASSWORD,
        max_retries=MAX_RETRIES
    )
    
    try:
        # 连接并复制
        if copier.connect():
            copier.copy_recent_files(REMOTE_PATH, LOCAL_PATH, FILE_COUNT, SKIP_EXISTING)
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
    except ImportError:
        print("请先安装所需依赖: pip install paramiko")
        sys.exit(1)
        
    main()