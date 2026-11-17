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
        
    def get_recent_files(self, local_path, file_count=30):
        """获取本地目录中最新的file_count个文件"""
        try:
            # 列出本地目录中的所有文件
            files = os.listdir(local_path)
            
            # 过滤出符合日期格式的文件 (YYYYMMDD.xxx)
            date_files = []
            for f in files:
                # 检查是否为文件而不是目录
                file_path = os.path.join(local_path, f)
                if not os.path.isfile(file_path):
                    continue
                    
                # 使用split方法提取日期部分
                if '.' in f:
                    date_part = f.split('.')[0]
                    
                    # 检查是否为8位数字
                    if len(date_part) == 8 and date_part.isdigit():
                        try:
                            date = datetime.strptime(date_part, '%Y%m%d')
                            # 获取文件修改时间用于排序
                            mtime = os.path.getmtime(file_path)
                            date_files.append((f, date, mtime))
                        except ValueError:
                            # 日期格式无效，跳过
                            continue
            
            # 按修改时间排序并获取最新的文件
            date_files.sort(key=lambda x: x[2], reverse=True)
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
            
    def copy_file_with_retry(self, local_path, remote_path, file_name, skip_existing=True, max_retries=3):
        """复制单个文件到远程，支持重试"""
        local_file = f"{local_path}/{file_name}"
        remote_file = f"{remote_path}/{file_name}"
        
        # 检查远程文件是否已存在
        if skip_existing:
            try:
                self.sftp.stat(remote_file)
                print(f"跳过已存在的远程文件: {file_name}")
                return True
            except FileNotFoundError:
                # 文件不存在，继续复制
                pass
            except Exception as e:
                print(f"检查远程文件状态失败: {e}")
            
        for attempt in range(max_retries):
            try:
                # 确保远程目录存在
                try:
                    self.sftp.stat(remote_path)
                except FileNotFoundError:
                    # 如果目录不存在，创建它
                    self._create_remote_directory(remote_path)
                
                # 使用SFTP复制文件到远程
                self.sftp.put(local_file, remote_file)
                
                # 验证文件是否成功复制（检查远程文件大小）
                local_size = os.path.getsize(local_file)
                remote_attrs = self.sftp.stat(remote_file)
                remote_size = remote_attrs.st_size
                
                if remote_size == local_size:
                    print(f"成功复制到远程: {file_name} ({remote_size} 字节)")
                    return True
                else:
                    raise Exception(f"文件大小不匹配: 本地 {local_size} 字节, 远程 {remote_size} 字节")
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"复制文件 {file_name} 尝试 {attempt+1}/{max_retries} 失败: {e}")
                    time.sleep(10)  # 等待10秒后重试
                    
                    # 删除可能损坏的远程文件
                    try:
                        self.sftp.remove(remote_file)
                    except:
                        pass
                else:
                    print(f"复制文件 {file_name} 失败: {e}")
                    return False
    
    def _create_remote_directory(self, remote_path):
        """递归创建远程目录"""
        try:
            self.sftp.stat(remote_path)
            return  # 目录已存在
        except FileNotFoundError:
            # 递归创建父目录
            parent_dir = os.path.dirname(remote_path)
            if parent_dir and parent_dir != remote_path:
                self._create_remote_directory(parent_dir)
            
            # 创建当前目录
            self.sftp.mkdir(remote_path)
            print(f"创建远程目录: {remote_path}")
            
    def copy_recent_files(self, local_path, remote_path, file_count=30, skip_existing=True):
        """复制最新的file_count个文件到远程"""
        if not self.ssh:
            print("请先建立SSH连接")
            return False
            
        # 确保本地目录存在
        if not os.path.exists(local_path):
            print(f"本地目录不存在: {local_path}")
            return False
        
        # 获取最新的文件
        recent_files = self.get_recent_files(local_path, file_count)
        
        if not recent_files:
            print("未找到符合条件的文件")
            return False
        
        print(f"开始复制 {len(recent_files)} 个文件到远程...")
        
        # 复制每个文件
        success_count = 0
        for file_name in recent_files:
            if self.copy_file_with_retry(local_path, remote_path, file_name, skip_existing):
                success_count += 1
        
        print(f"复制完成: 成功 {success_count}/{len(recent_files)} 个文件")
        return success_count > 0

def main():
    # 配置参数 - 请修改这些值
    HOST = "192.168.1.107"
    PORT = 22
    USERNAME = "root"  # 替换为你的用户名
    PASSWORD = "000416bb"  # 替换为你的密码
    
    LOCAL_PATH = "/common/data_triggers/max_15s_turnover/mdata"  # 本地路径
    REMOTE_PATH = "/common/data_triggers_online/max_15s_turnover/mdata"  # 远程路径
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
            copier.copy_recent_files(LOCAL_PATH, REMOTE_PATH, FILE_COUNT, SKIP_EXISTING)
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