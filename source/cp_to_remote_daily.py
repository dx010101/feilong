import os
import sys
from cp_to_remote_single_dir import SSHFullCopier

def main():
    # 配置参数 - 请修改这些值
    HOST = "192.168.1.107"
    PORT = 22
    USERNAME = "root"  # 替换为你的用户名
    PASSWORD = "000416bb"  # 替换为你的密码
    
    local_dir = "/common/data_triggers/max_15s_turnover_tushare"
    remote_dir = "/common/data_triggers/max_15s_turnover_tushare_online"

    path_map = [
        (os.path.join(local_dir, "trade_cutoff.jsonl"), os.path.join(remote_dir, "trade_cutoff.jsonl"), False, False),
        (os.path.join(local_dir, "trigger_cutoff.jsonl"), os.path.join(remote_dir, "trigger_cutoff.jsonl"), False, False),
        (os.path.join(local_dir, "buffer_input"), os.path.join(remote_dir, "buffer_input"), True, True),
        (os.path.join(local_dir, "buffer_output"), os.path.join(remote_dir, "buffer_output"), True, True),
        # (os.path.join(local_dir, "data_logs"), os.path.join(remote_dir, "data_logs"), True),
        (os.path.join(local_dir, "logs"), os.path.join(remote_dir, "logs"),True, True),
        (os.path.join(local_dir, "trade_signal"), os.path.join(remote_dir, "trade_signal"), True, True),
        (os.path.join(local_dir, "tsdata"), os.path.join(remote_dir, "tsdata"),True, False),
        (os.path.join(local_dir, "mdata"), os.path.join(remote_dir, "mdata"), True, True),
        (os.path.join(local_dir, "xdata_cpp"), os.path.join(remote_dir, "xdata_cpp"), True, True),
        (os.path.join(local_dir, "ydata"), os.path.join(remote_dir, "ydata"), True, False),
        (os.path.join(local_dir, "pre_ydata"), os.path.join(remote_dir, "pre_ydata"),True, True),


    ]

    MAX_RETRIES = 3  # 最大重试次数
    
    # 创建复制器实例
    copier = SSHFullCopier(
        host=HOST,
        port=PORT,
        username=USERNAME,
        password=PASSWORD,
        max_retries=MAX_RETRIES
    )
    for local_path, remote_path, is_dir, skip in path_map:
        print(f"\n copy local dir {local_path } \n")
        try:
            # 连接并复制
            if copier.connect():
                if is_dir:
                    copier.copy_full_directory(local_path, remote_path, skip)
                else:
                    copier.copy_file_with_retry(local_path, remote_path, MAX_RETRIES)
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