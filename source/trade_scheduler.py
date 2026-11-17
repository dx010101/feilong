import docker
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('docker_scheduler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DockerContainerScheduler:
    def __init__(self):
        try:
            self.client = docker.from_env()
            logger.info("Docker客户端初始化成功")
        except Exception as e:
            logger.error(f"Docker客户端初始化失败: {e}")
            sys.exit(1)
    
    def start_container(self, container_name):
        """启动容器"""
        try:
            container = self.client.containers.get(container_name)
            if container.status != 'running':
                container.start()
                logger.info(f"容器 {container_name} 启动成功")
            else:
                logger.info(f"容器 {container_name} 已经在运行中")
        except docker.errors.NotFound:
            logger.error(f"容器 {container_name} 不存在")
        except Exception as e:
            logger.error(f"启动容器 {container_name} 失败: {e}")
    
    def stop_container(self, container_name):
        """停止容器"""
        try:
            container = self.client.containers.get(container_name)
            if container.status == 'running':
                container.stop()
                logger.info(f"容器 {container_name} 停止成功")
            else:
                logger.info(f"容器 {container_name} 不在运行状态")
        except docker.errors.NotFound:
            logger.error(f"容器 {container_name} 不存在")
        except Exception as e:
            logger.error(f"停止容器 {container_name} 失败: {e}")
    
    def start_data_clean(self):
        """启动data_clean容器"""
        logger.info("执行data_clean容器启动任务")
        self.start_container('data_clean')
    
    def start_trading_containers(self):
        """启动交易相关容器"""
        logger.info("执行交易容器启动任务")
        self.start_container('cpp_trader')
        # self.start_container('cpp_trader_mirror')
        self.start_container('py_norm')
        # self.start_container('py_norm_mirror')
        self.stop_container('run_feature_only_cpp')
    
    def stop_trading_containers(self):
        """停止交易相关容器"""
        logger.info("执行交易容器停止任务")
        self.stop_container('cpp_trader')
        # self.stop_container('cpp_trader_mirror')
        self.stop_container('py_norm')
        # self.stop_container('py_norm_mirror')
        self.start_container('run_feature_only_cpp')
    
    def check_containers_status(self):
        """检查所有容器状态"""
        logger.info("检查容器状态")
        containers = ['data_clean', 'cpp_trader', 'py_norm', 'run_feature_only_cpp']
        for container_name in containers:
            try:
                container = self.client.containers.get(container_name)
                logger.info(f"容器 {container_name} 状态: {container.status}")
            except docker.errors.NotFound:
                logger.warning(f"容器 {container_name} 不存在")
            except Exception as e:
                logger.error(f"检查容器 {container_name} 状态失败: {e}")

def main():
    scheduler = DockerContainerScheduler()
    
    # 创建调度器
    sched = BlockingScheduler()
    
    # 添加定时任务
    
    # data_clean: 每天18:20启动
    sched.add_job(
        scheduler.start_data_clean,
        trigger=CronTrigger(hour=18, minute=30),
        id='start_data_clean',
        name='启动data_clean容器'
    )
    
    # cpp_trader和py_norm: 每天8:30启动
    sched.add_job(
        scheduler.start_trading_containers,
        trigger=CronTrigger(hour=9, minute=5),
        id='start_trading_containers',
        name='启动交易容器'
    )
    
    # cpp_trader和py_norm: 每天15:05停止
    sched.add_job(
        scheduler.stop_trading_containers,
        trigger=CronTrigger(hour=15, minute=5),
        id='stop_trading_containers',
        name='停止交易容器'
    )
    
    # 每30分钟检查一次容器状态（可选）
    sched.add_job(
        scheduler.check_containers_status,
        trigger='interval',
        minutes=30,
        id='check_containers_status',
        name='检查容器状态'
    )
    
    # 启动时立即检查一次容器状态
    scheduler.check_containers_status()
    
    # 打印调度任务信息
    jobs = sched.get_jobs()
    logger.info("已配置的调度任务:")
    for job in jobs:
        logger.info(f"- {job.name} (ID: {job.id})")
    
    logger.info("Docker容器调度器已启动，按 Ctrl+C 退出")
    
    try:
        sched.start()
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭调度器...")
    except Exception as e:
        logger.error(f"调度器运行错误: {e}")
    finally:
        sched.shutdown()
        logger.info("调度器已关闭")

if __name__ == "__main__":
    main()