#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import paramiko
import os
import sys
import time
from stat import S_ISDIR, S_ISREG

class SSHFullCopier:
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
        
    def ensure_remote_dir(self, remote_path):
        """确保远程目录存在"""
        try:
            self.sftp.stat(remote_path)
        except FileNotFoundError:
            # 递归创建目录
            dirname, basename = os.path.split(remote_path)
            if dirname and dirname != '/':
                self.ensure_remote_dir(dirname)
            print(f"创建远程目录: {remote_path}")
            self.sftp.mkdir(remote_path)
    
    def copy_file_with_retry(self, local_path, remote_path, max_retries=3):
        """复制单个文件到远程，支持重试"""
        # print("trying to copy file path:", remote_path)
        for attempt in range(max_retries):
            try:
                # 确保远程目录存在
                remote_dir = os.path.dirname(remote_path)
                self.ensure_remote_dir(remote_dir)
                
                # 使用SFTP上传文件
                self.sftp.put(local_path, remote_path)
                
                # 验证文件是否成功上传（检查文件大小）
                local_size = os.path.getsize(local_path)
                remote_attr = self.sftp.stat(remote_path)
                remote_size = remote_attr.st_size
                
                if local_size == remote_size:
                    print(f"成功上传文件: {local_path} -> {remote_path}")
                    return True
                else:
                    raise Exception(f"文件大小不匹配: 本地{local_size}字节, 远程{remote_size}字节")
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"上传文件 {local_path} 尝试 {attempt+1}/{max_retries} 失败: {e}")
                    time.sleep(10)  # 等待10秒后重试
                    
                    # 删除可能损坏的远程文件
                    try:
                        self.sftp.remove(remote_path)
                    except:
                        pass
                else:
                    print(f"上传文件 {local_path} 失败: {e}")
                    return False
    
    def copy_directory_recursive(self, local_path, remote_path, skip_existing=True):
        """递归复制整个目录结构到远程"""
        print(f"处理目录: {local_path}")
        
        # 确保远程目录存在
        self.ensure_remote_dir(remote_path)
        
        try:
            # 遍历本地目录中的所有项目
            for item_name in os.listdir(local_path):
                local_item_path = os.path.join(local_path, item_name)
                remote_item_path = os.path.join(remote_path, item_name)
                
                # 如果是目录，递归处理
                if os.path.isdir(local_item_path):
                    self.copy_directory_recursive(local_item_path, remote_item_path, skip_existing)
                
                # 如果是文件，复制文件
                elif os.path.isfile(local_item_path):
                    # 检查是否跳过已存在的文件
                    if skip_existing:
                        try:
                            remote_attr = self.sftp.stat(remote_item_path)
                            local_size = os.path.getsize(local_item_path)
                            remote_size = remote_attr.st_size
                            
                            if local_size == remote_size:
                                # print(f"跳过已存在的文件: {remote_item_path}")
                                continue
                        except FileNotFoundError:
                            pass  # 文件不存在，需要上传
                    
                    self.copy_file_with_retry(local_item_path, remote_item_path)
        
        except Exception as e:
            print(f"处理目录 {local_path} 时出错: {e}")
    
    def copy_full_directory(self, local_path, remote_path, skip_existing=True):
        """复制整个本地目录到远程"""
        if not self.ssh:
            print("请先建立SSH连接")
            return False
            
        # 检查本地路径是否存在
        if not os.path.exists(local_path):
            print(f"本地路径不存在: {local_path}")
            return False
            
        print(f"开始复制整个目录: {local_path} -> {remote_path}")
        start_time = time.time()
        
        try:
            # 递归复制整个目录
            self.copy_directory_recursive(local_path, remote_path, skip_existing)
            
            end_time = time.time()
            duration = end_time - start_time
            print(f"目录复制完成! 耗时: {duration:.2f} 秒")
            return True
            
        except Exception as e:
            print(f"复制目录失败: {e}")
            return False

def main():
    # 配置参数 - 请修改这些值
    HOST = "192.168.1.107"
    PORT = 22
    USERNAME = "root"  # 替换为你的用户名
    PASSWORD = "000416bb"  # 替换为你的密码
    
    # LOCAL_PATH = "/common/data_triggers/max_15s_turnover/tsdata"  # 本地路径
    # REMOTE_PATH = "/common/data_triggers/max_15s_turnover/tsdata"  # 远程路径
    LOCAL_PATH = "/common/data_3s_feather_full/20251201"  # 本地路径
    REMOTE_PATH = "/common/data_3s_feather_full_online/20251201"  # 远程路径
    SKIP_EXISTING = True  # 是否跳过已存在的文件
    MAX_RETRIES = 3  # 最大重试次数
    
    # 创建复制器实例
    copier = SSHFullCopier(
        host=HOST,
        port=PORT,
        username=USERNAME,
        password=PASSWORD,
        max_retries=MAX_RETRIES
    )
    
    try:
        # 连接并复制
        if copier.connect():
            copier.copy_full_directory(LOCAL_PATH, REMOTE_PATH, SKIP_EXISTING)
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