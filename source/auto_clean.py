import os
import subprocess
import sys
import logging
import time
# Create a custom logger
logger = logging.getLogger(__name__)

# Create handlers
console_handler = logging.StreamHandler()

# Create formatters and add them to handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)

# Set the logging level to DEBUG for more detailed output
logger.setLevel(logging.DEBUG)


scripts = [
    {
        "name": "华鑫3s数据下载",
        "step": 1,
        "project_root": "/public/paul/s3_downloader_huaxin",
        "rel_path": "run.py",
        "args": [],
        "timeout": 3600
    },
    # {
    #     "name": "Baostock日度数据下载 （从开发服务器同步csv数据）", 
    #     "step": 2,
    #     "project_root": "/public/paul/scripts",
    #     "rel_path": "cp_baostock_daily.py",
    #     "args": [],
    #     "timeout": 3600
    # },
    # {
    #     "name": "Baostock日度数据下载（不下载，只更新feather数据）", 
    #     "step": 3,
    #     "project_root": "/public/paul/daily_downloader_baostock",
    #     "rel_path": "run.py",
    #     "args": [],
    #     "timeout": 1000
    # },
    {
        "name": "Tushare日度数据下载（不下载，只更新feather数据）", 
        "step": 2,
        "project_root": "/public/paul/daily_downloader_tushare",
        "rel_path": "run.py",
        "args": [],
        "timeout": 1000
    },
    {
        "name": "trigger和ydata的数据生成",
        "step": 3,
        "project_root": "/public/paul/feature_only_py",
        "rel_path": "tests/test_3s_trigger_15s_turnover.py",
        "args": [],
        "timeout": 2000
    },
    {
        "name": "cpp版xdata的数据生成",
        "step": 4,
        "project_root": "/public/paul/feature_only_py",
        "rel_path": "tests/test_py_feature_gen.py",
        "args": [],
        "timeout": 2200
    },
    {
        "name": "trigger和trade cutoff阈值生成",
        "step": 5,
        "project_root": "/public/paul/feature_norm",
        "rel_path": "scripts/update_triggers.py",
        "args": [],
        "timeout": 6000
    },
    # {
    #     "name": "同步数据到开发服",
    #     "step": 6,
    #     "project_root": "/public/paul/scripts",
    #     "rel_path": "cp_to_remote_daily.py",
    #     "args": [],
    #     "timeout": 3000
    # },

]

if __name__ == "__main__":
    target_step = 0
    # 获取当前环境变量并传递给子进程
    env = os.environ.copy()
    
    for script_info in scripts:
        name = script_info.get("name", "未知脚本")
        step = script_info.get("step", None)
        rel_path = script_info.get("rel_path")
        project_root = script_info.get("project_root")
        args = script_info.get("args", [])
        timeout = script_info.get("timeout", 10)
        
        if not step > target_step:
            continue
            
        if not rel_path:
            logger.info(f"跳过 {name}: 未指定脚本路径")
            continue
        
        logger.info(f"正在执行步骤: {step}, 任务： {name}")
        
        try:
            # 确保项目根目录存在
            if not os.path.exists(project_root):
                logger.error(f"项目根目录不存在: {project_root}")
                continue
                
            # 构建绝对路径
            abs_path = os.path.join(project_root, rel_path)
            if not os.path.exists(abs_path):
                logger.error(f"脚本文件不存在: {abs_path}")
                continue
                
            logger.debug(f"执行脚本路径: {abs_path}")
            logger.debug(f"工作目录: {project_root}")
            
            # 构建命令 - 使用绝对路径更可靠
            command = [sys.executable, abs_path] + args
            
            start = time.time()
            # 传递环境变量，增加输出缓冲区大小
            result = subprocess.run(
                command,
                cwd=project_root,
                env=env,  # 传递环境变量
                capture_output=True,
                text=True,
                timeout=timeout,
                bufsize=1  # 行缓冲，有助于实时输出
            )
            end = time.time()
            duration = end - start
            
            if result.returncode == 0:
                logger.info(f"✓ 【{name}】 执行成功, 耗时 {duration:.2f}秒")
                if result.stdout.strip():
                    logger.debug(f"输出: {result.stdout.strip()}")
            else:
                logger.error(f"✗ 【{name}】 执行失败，返回码: {result.returncode}，耗时 {duration:.2f}秒")
                if result.stdout.strip():
                    logger.error(f"标准输出: {result.stdout.strip()}")
                if result.stderr.strip():
                    logger.error(f"错误输出: {result.stderr.strip()}")
                    
        except subprocess.TimeoutExpired:
            logger.error(f"✗ 【{name}】 执行超时 (超过 {timeout} 秒)")
        except Exception as e:
            logger.exception(f"✗ 执行 【{name}】 时发生异常")
