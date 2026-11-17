import os
import sys
from remote_copy_files import SSHFileCopier

import zipfile
import os
import shutil


def update_fields_folder(zip_path: str, extract_path: str):
    """
    解压 zip 文件覆盖目标文件夹，避免双重目录
    zip_path = '/common/data_daily_update/fields.zip'
    extract_path = '/common/data_daily_update'
    """
    # 步骤1：如果目标文件夹存在，先删除它
    if os.path.exists(extract_path):
        print(f"删除旧的文件夹: {extract_path}")
        shutil.rmtree(extract_path)
    
    # 步骤2：创建临时目录
    temp_dir = extract_path + '_temp'
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # 步骤3：解压到临时目录
        print(f"解压 {zip_path} 到临时目录")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # 步骤4：检查临时目录的内容
        items = os.listdir(temp_dir)
        print(f"临时目录内容: {items}")
        
        # 如果只有一个文件夹，且名字是'fields'，则将其内容移出
        if len(items) == 1 and items[0] == 'fields':
            print("检测到顶层fields文件夹，正在调整目录结构...")
            inner_dir = os.path.join(temp_dir, 'fields')
            
            # 创建最终的目标目录
            os.makedirs(extract_path, exist_ok=True)
            
            # 移动内部所有内容到目标目录
            for item in os.listdir(inner_dir):
                src = os.path.join(inner_dir, item)
                dst = os.path.join(extract_path, item)
                shutil.move(src, dst)
                print(f"移动: {item}")
        else:
            # 如果没有顶层文件夹，直接移动所有内容
            print("直接移动所有内容...")
            os.makedirs(extract_path, exist_ok=True)
            for item in items:
                src = os.path.join(temp_dir, item)
                dst = os.path.join(extract_path, item)
                shutil.move(src, dst)
                print(f"移动: {item}")
        
        print("解压缩完成！")
        
    finally:
        # 清理临时目录
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


def main():
    # 配置参数 - 请修改这些值
    HOST = "192.168.1.107"
    PORT = 22
    USERNAME = "root"  # 替换为你的用户名
    PASSWORD = "000416bb"  # 替换为你的密码
    
    remote_dir = "/common/data_daily_update"
    local_dir = "/common/data_daily_update"
    dir_name = "fields"
    file_name = f"{dir_name}.zip"

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

            copier.copy_file_with_retry(remote_dir, local_dir, file_name, skip_existing=False, max_retries=MAX_RETRIES)
            # 尝试解压缩
            update_fields_folder(zip_path=f"{local_dir}/{file_name}", extract_path=f"{local_dir}/{dir_name}")
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