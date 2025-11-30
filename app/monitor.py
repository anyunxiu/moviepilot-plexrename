"""
目录监控模块

监控源目录的文件变化，自动触发整理
"""
import os
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from typing import Callable

logger = logging.getLogger(__name__)


class MediaFileHandler(FileSystemEventHandler):
    """媒体文件事件处理器"""
    
    def __init__(self, callback: Callable[[str], None], 
                 extensions: tuple = ('.mp4', '.mkv', '.avi', '.mov')):
        """
        :param callback: 文件创建时的回调函数
        :param extensions: 要监控的文件扩展名
        """
        self.callback = callback
        self.extensions = extensions
        super().__init__()
    
    def on_created(self, event):
        """文件创建事件"""
        if event.is_directory:
            return
        
        if not event.src_path.lower().endswith(self.extensions):
            return
        
        logger.info(f"New file detected: {event.src_path}")
        
        # 等待文件写入完成（简单延迟）
        time.sleep(2)
        
        # 调用回调函数
        try:
            self.callback(event.src_path)
        except Exception as e:
            logger.error(f"Error processing {event.src_path}: {e}")


class DirectoryMonitor:
    """目录监控器"""
    
    def __init__(self):
        self.observer = Observer()
        self.watches = {}
    
    def add_watch(self, path: str, callback: Callable[[str], None], 
                  extensions: tuple = ('.mp4', '.mkv', '.avi', '.mov')):
        """
        添加监控路径
        
        :param path: 要监控的目录路径
        :param callback: 文件创建时的回调函数
        :param extensions: 文件扩展名过滤
        """
        if not os.path.exists(path):
            logger.warning(f"Path does not exist: {path}")
            return False
        
        if path in self.watches:
            logger.warning(f"Path already being watched: {path}")
            return False
        
        handler = MediaFileHandler(callback, extensions)
        watch = self.observer.schedule(handler, path, recursive=True)
        self.watches[path] = watch
        
        logger.info(f"Started watching: {path}")
        return True
    
    def remove_watch(self, path: str):
        """移除监控路径"""
        if path not in self.watches:
            logger.warning(f"Path not being watched: {path}")
            return False
        
        watch = self.watches.pop(path)
        self.observer.unschedule(watch)
        
        logger.info(f"Stopped watching: {path}")
        return True
    
    def start(self):
        """启动监控"""
        if not self.observer.is_alive():
            self.observer.start()
            logger.info("Directory monitor started")
    
    def stop(self):
        """停止监控"""
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            logger.info("Directory monitor stopped")
    
    def is_running(self) -> bool:
        """检查监控是否正在运行"""
        return self.observer.is_alive()
