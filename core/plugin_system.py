"""
插件系统 - 可扩展的模块化架构

参考 Django App 和 FastAPI 依赖注入设计
"""
import importlib
import inspect
from abc import ABC, abstractmethod
from typing import Dict, List, Type, Any, Optional, Callable
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PluginMetadata:
    """插件元数据"""
    name: str
    version: str
    description: str
    author: str
    dependencies: List[str]
    entry_point: str  # 插件入口类路径


class PluginInterface(ABC):
    """
    插件接口基类
    
    所有插件必须继承此类并实现必要方法
    """
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """返回插件元数据"""
        pass
    
    @abstractmethod
    def initialize(self, context: Dict[str, Any]) -> None:
        """
        初始化插件
        
        Args:
            context: 应用上下文，包含配置、数据库连接等
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """关闭插件，释放资源"""
        pass
    
    def get_health(self) -> Dict[str, Any]:
        """
        返回插件健康状态
        
        Returns:
            {"status": "healthy|degraded|unhealthy", "details": {...}}
        """
        return {"status": "healthy", "details": {}}


class AnalyzerPlugin(PluginInterface):
    """分析器插件接口"""
    
    @abstractmethod
    def analyze(self, data: Any) -> Dict[str, Any]:
        """执行分析"""
        pass
    
    @abstractmethod
    def supports(self, data_type: str) -> bool:
        """检查是否支持特定数据类型"""
        pass


class DataSourcePlugin(PluginInterface):
    """数据源插件接口"""
    
    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> bool:
        """连接数据源"""
        pass
    
    @abstractmethod
    def fetch(self, query: Dict[str, Any]) -> List[Dict]:
        """获取数据"""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """获取数据schema"""
        pass


class ExporterPlugin(PluginInterface):
    """导出器插件接口"""
    
    @abstractmethod
    def export(self, data: Any, format_type: str) -> str:
        """
        导出数据
        
        Returns:
            导出文件路径
        """
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """返回支持的格式列表"""
        pass


class PluginManager:
    """
    插件管理器
    
    负责插件的加载、注册、生命周期管理
    
    使用示例：
        pm = PluginManager()
        pm.load_plugin("my_plugin.Analyzer")
        pm.initialize_all({"db": db_connection})
    """
    
    def __init__(self):
        self._plugins: Dict[str, PluginInterface] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._context: Optional[Dict[str, Any]] = None
    
    def load_plugin(self, plugin_path: str) -> bool:
        """
        加载插件
        
        Args:
            plugin_path: 插件类路径，如 "plugins.video.VideoAnalyzer"
            
        Returns:
            是否成功加载
        """
        try:
            # 解析模块路径
            module_path, class_name = plugin_path.rsplit(".", 1)
            
            # 动态导入模块
            module = importlib.import_module(module_path)
            
            # 获取插件类
            plugin_class = getattr(module, class_name)
            
            # 验证是 PluginInterface 的子类
            if not issubclass(plugin_class, PluginInterface):
                logger.error(f"{class_name} 不是有效的插件类")
                return False
            
            # 实例化插件
            plugin = plugin_class()
            
            # 检查依赖
            metadata = plugin.metadata
            for dep in metadata.dependencies:
                if dep not in self._plugins:
                    logger.error(f"插件 {metadata.name} 依赖 {dep} 未加载")
                    return False
            
            # 注册插件
            self._plugins[metadata.name] = plugin
            logger.info(f"插件加载成功: {metadata.name} v{metadata.version}")
            return True
            
        except Exception as e:
            logger.error(f"加载插件失败 {plugin_path}: {e}")
            return False
    
    def load_plugins_from_directory(self, directory: str) -> int:
        """
        从目录加载所有插件
        
        Args:
            directory: 插件目录
            
        Returns:
            加载成功的插件数量
        """
        import os
        import pkgutil
        
        count = 0
        if not os.path.exists(directory):
            return count
        
        # 将目录添加到 Python 路径
        import sys
        if directory not in sys.path:
            sys.path.insert(0, directory)
        
        # 遍历目录中的所有模块
        for importer, modname, ispkg in pkgutil.iter_modules([directory]):
            try:
                module = importlib.import_module(modname)
                
                # 查找模块中的插件类
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, PluginInterface) and 
                        obj is not PluginInterface and
                        not inspect.isabstract(obj)):
                        
                        if self.load_plugin(f"{modname}.{name}"):
                            count += 1
                            
            except Exception as e:
                logger.warning(f"加载模块 {modname} 失败: {e}")
        
        return count
    
    def initialize_all(self, context: Dict[str, Any]) -> None:
        """
        初始化所有插件
        
        Args:
            context: 应用上下文
        """
        self._context = context

        # 按依赖顺序初始化
        initialized = set()
        initializing = set()  # 环检测：记录正在初始化中的插件

        def init_plugin(name: str, plugin: PluginInterface):
            if name in initialized:
                return

            # 检测循环依赖
            if name in initializing:
                raise ValueError(f"检测到插件循环依赖，涉及插件: {name}")

            initializing.add(name)

            # 先初始化依赖
            for dep in plugin.metadata.dependencies:
                if dep in self._plugins:
                    init_plugin(dep, self._plugins[dep])

            # 初始化当前插件
            try:
                plugin.initialize(context)
                initialized.add(name)
                initializing.discard(name)
                logger.info(f"插件初始化成功: {name}")
            except Exception as e:
                initializing.discard(name)
                logger.error(f"插件初始化失败 {name}: {e}")
        
        for name, plugin in self._plugins.items():
            init_plugin(name, plugin)
    
    def shutdown_all(self) -> None:
        """关闭所有插件"""
        for name, plugin in self._plugins.items():
            try:
                plugin.shutdown()
                logger.info(f"插件关闭成功: {name}")
            except Exception as e:
                logger.error(f"插件关闭失败 {name}: {e}")
    
    def get_plugin(self, name: str) -> Optional[PluginInterface]:
        """获取插件实例"""
        return self._plugins.get(name)
    
    def get_plugins_by_type(self, plugin_type: Type) -> List[PluginInterface]:
        """
        获取特定类型的所有插件
        
        Args:
            plugin_type: 插件类型，如 AnalyzerPlugin
            
        Returns:
            插件实例列表
        """
        return [p for p in self._plugins.values() if isinstance(p, plugin_type)]
    
    def register_hook(self, event: str, handler: Callable) -> None:
        """
        注册事件钩子
        
        Args:
            event: 事件名称
            handler: 处理函数
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(handler)
    
    def trigger_hook(self, event: str, *args, **kwargs) -> List[Any]:
        """
        触发事件钩子
        
        Args:
            event: 事件名称
            *args, **kwargs: 传递给处理函数的参数
            
        Returns:
            所有处理函数的返回值列表
        """
        results = []
        for handler in self._hooks.get(event, []):
            try:
                result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(f"钩子执行失败 {event}: {e}")
        return results
    
    def get_health(self) -> Dict[str, Any]:
        """获取所有插件健康状态"""
        return {
            name: plugin.get_health()
            for name, plugin in self._plugins.items()
        }
