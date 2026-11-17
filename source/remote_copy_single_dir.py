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
        
    def is_dir(self, path):
        """检查路径是否为目录"""
        try:
            return S_ISDIR(self.sftp.stat(path).st_mode)
        except IOError:
            return False
            
    def is_file(self, path):
        """检查路径是否为文件"""
        try:
            return S_ISREG(self.sftp.stat(path).st_mode)
        except IOError:
            return False
    
    def copy_file_with_retry(self, remote_path, local_path, max_retries=3):
        """复制单个文件，支持重试"""
        for attempt in range(max_retries):
            try:
                # 确保本地目录存在
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                # 使用SFTP复制文件
                self.sftp.get(remote_path, local_path)
                
                # 验证文件是否成功复制
                if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                    print(f"成功复制文件: {remote_path} -> {local_path}")
                    return True
                else:
                    raise Exception("复制后文件为空或不存在")
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"复制文件 {remote_path} 尝试 {attempt+1}/{max_retries} 失败: {e}")
                    time.sleep(10)  # 等待10秒后重试
                    
                    # 删除可能损坏的部分文件
                    if os.path.exists(local_path):
                        try:
                            os.remove(local_path)
                        except:
                            pass
                else:
                    print(f"复制文件 {remote_path} 失败: {e}")
                    return False
    
    def copy_directory_recursive(self, remote_path, local_path, skip_existing=True):
        """递归复制整个目录结构"""
        print(f"处理目录: {remote_path}")
        
        # 确保本地目录存在
        os.makedirs(local_path, exist_ok=True)
        
        try:
            # 列出远程目录中的所有项目
            items = self.sftp.listdir_attr(remote_path)
            
            for item in items:
                remote_item_path = os.path.join(remote_path, item.filename)
                local_item_path = os.path.join(local_path, item.filename)
                
                # 如果是目录，递归处理
                if S_ISDIR(item.st_mode):
                    self.copy_directory_recursive(remote_item_path, local_item_path, skip_existing)
                
                # 如果是文件，复制文件
                elif S_ISREG(item.st_mode):
                    # 检查是否跳过已存在的文件
                    if skip_existing and os.path.exists(local_item_path):
                        # 可选：比较文件大小，如果不同则重新复制
                        remote_size = item.st_size
                        local_size = os.path.getsize(local_item_path) if os.path.exists(local_item_path) else 0
                        
                        if remote_size == local_size:
                            print(f"跳过已存在的文件: {remote_item_path}")
                            continue
                    
                    self.copy_file_with_retry(remote_item_path, local_item_path)
        
        except Exception as e:
            print(f"处理目录 {remote_path} 时出错: {e}")
    
    def copy_full_directory(self, remote_path, local_path, skip_existing=True):
        """复制整个远程目录到本地"""
        if not self.ssh:
            print("请先建立SSH连接")
            return False
            
        # 确保本地基础目录存在
        os.makedirs(local_path, exist_ok=True)
        
        print(f"开始复制整个目录: {remote_path} -> {local_path}")
        start_time = time.time()
        
        try:
            # 递归复制整个目录
            self.copy_directory_recursive(remote_path, local_path, skip_existing)
            
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
    
    REMOTE_PATH = "/common/data_daily/data_daily_non_adjust"  # 替换为你的远程路径
    LOCAL_PATH = "/common/data_daily/data_daily_non_adjust"  # 替换为你的本地路径
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
            copier.copy_full_directory(REMOTE_PATH, LOCAL_PATH, SKIP_EXISTING)
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