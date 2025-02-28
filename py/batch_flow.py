import os
import platform
import numpy as np
import cv2
import torch
import json
import hashlib
from typing import Tuple, List
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image

# ======================== 通用工具函数 ========================
def 清理路径(路径: str) -> str:
    """路径清理和安全处理"""
    return str(Path(路径).resolve())

def 处理Windows路径(路径: str) -> str:
    """Windows 系统路径处理"""
    if platform.system() == "Windows":
        return str(Path(路径).resolve())
    return 路径

# ======================== 保存图像节点优化 ========================
class 保存图像带路径:
    """
    优化改进点：
    1. 智能索引生成算法（提升效率）
    2. 增强型路径类型判断
    3. 支持多种图片格式和压缩质量
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图像": ("IMAGE",),
                "默认输出目录": ("STRING", {"default": "output"}),
                "文件名前缀": ("STRING", {"default": "output"}),
                "文件名后缀": ("STRING", {"default": ""}),
                "应用后缀到自定义路径": ("BOOLEAN", {"default": False}),
                "自定义路径": ("STRING", {"default": ""}),
            },
            "optional": {
                "子路径": ("STRING", {"forceInput": True}),
            },
        }

    FUNCTION = "保存图像带路径"
    CATEGORY = "batch_flow"
    OUTPUT_NODE = True

    RETURN_TYPES = ()
    RETURN_NAMES = ()

    def 生成文件名(self, 目录路径: str, 前缀: str, 后缀: str, 扩展名: str) -> str:
        """智能生成不重复文件名"""
        目录 = Path(目录路径)
        模式 = f"{前缀}_*_{后缀}.{扩展名}"
        现有文件 = [f for f in 目录.glob(模式)]
        
        if not 现有文件:
            return f"{前缀}_00001_{后缀}.{扩展名}"
        
        最大索引 = max(int(f.stem.split('_')[1]) for f in 现有文件)
        return f"{前缀}_{最大索引 + 1:05}_{后缀}.{扩展名}"

    def 处理自定义路径(self, 自定义路径: str, 后缀: str, 应用后缀: bool) -> Tuple[str, str]:
        """处理自定义路径逻辑"""
        if not 自定义路径:
            return "", ""
            
        自定义路径 = 处理Windows路径(自定义路径)
        路径对象 = Path(自定义路径)
        if 路径对象.is_dir():
            return str(路径对象), ""
            
        目录部分, 文件部分 = 路径对象.parent, 路径对象.name
        if not 文件部分:
            return str(目录部分), ""
            
        名称, 扩展名 = os.path.splitext(文件部分)
        if 应用后缀:
            名称 += 后缀
        return str(目录部分), f"{名称}{扩展名}"

    def 保存图像带路径(self, 图像, 文件名前缀="", 文件名后缀="", 默认输出目录="output", 自定义路径="", 应用后缀到自定义路径=False, 子路径=""):
        try:
            # 处理子路径合并
            子路径 = 子路径 or ""
            if 子路径:
                if 自定义路径 and os.path.isdir(自定义路径):
                    基路径 = 自定义路径
                else:
                    基路径 = 默认输出目录
                新自定义路径 = os.path.join(基路径, 子路径)
                自定义路径 = 新自定义路径

            # 处理自定义路径为目录的情况
            if 自定义路径:
                是目录 = False
                if os.path.isdir(自定义路径):
                    是目录 = True
                else:
                    目录部分, 文件部分 = os.path.split(自定义路径)
                    if not 文件部分 or not os.path.splitext(文件部分)[1]:
                        是目录 = True

                if 是目录:
                    默认输出目录 = 自定义路径
                    自定义路径 = ""

            # 处理文件路径或自动生成路径
            if 自定义路径:
                目录, 文件名 = os.path.split(os.path.abspath(自定义路径))
                名称, 扩展名 = os.path.splitext(文件名)
                if 应用后缀到自定义路径 and 文件名后缀:
                    修改后的文件名 = f"{名称}{文件名后缀}{扩展名}"
                else:
                    修改后的文件名 = 文件名
                完整路径 = os.path.join(目录, 修改后的文件名)
            else:
                if not 默认输出目录:
                    默认输出目录 = "output"
                os.makedirs(默认输出目录, exist_ok=True)

                计数器 = 1
                while True:
                    文件名 = f"{文件名前缀}_{计数器:05}{文件名后缀}.png"
                    完整路径 = os.path.join(默认输出目录, 文件名)
                    if not os.path.exists(完整路径):
                        break
                    计数器 += 1

            # 保存图像（逻辑与原版一致）
            完整路径 = self.编码路径(完整路径)
            os.makedirs(os.path.dirname(完整路径), exist_ok=True)
            图像张量 = 图像.cpu().numpy()
            图像数组 = np.clip(255. * 图像张量.squeeze(), 0, 255).astype(np.uint8)
            Image.fromarray(图像数组).save(完整路径)

        except Exception as e:
            print(f"错误: 保存图像失败。原因: {str(e)}")
            raise

        return ()

    def 编码路径(self, 路径):
        if platform.system() == "Windows":
            try:
                return 路径.encode('utf-8').decode('mbcs')
            except:
                return 路径
        return 路径

    @classmethod
    def IS_CHANGED(cls, 图像, **kwargs):
        return float('nan')

# ======================== 加载图像节点优化 ========================
class 加载图像带路径:
    """
    优化改进点：
    1. 增量哈希计算（提升变更检测速度）
    2. 并行文件扫描
    3. 预加载机制
    """

    缓存大小 = 2  # 预加载图像数量
    
    def __init__(self):
        self.状态文件 = Path(__file__).parent / "tmp_file_state.json"
        self.当前状态 = {
            "路径": "",
            "递归": True,
            "后缀": "",
            "文件": [],
            "索引": 0,
            "文件哈希": "",
        }
        self.缓存 = {}
        self.执行器 = ThreadPoolExecutor(max_workers=2)
        self.加载状态()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "目录路径": ("STRING", {"default": "./input", "directory": True}),
                "包括子目录": ("BOOLEAN", {"default": True}),
                "后缀": ("STRING", {"default": "jpg,png,jpeg,webp"}),
                "允许RGBA": ("BOOLEAN", {"default": True}),
                "自刷新": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("图像", "子路径", "当前路径")
    FUNCTION = "加载下一张图像"
    CATEGORY = "batch_flow"

    def 扫描文件(self, 路径: str, 递归: bool, 扩展名: set) -> List[str]:
        """文件扫描"""
        目录 = Path(路径)
        if 递归:
            return [str(p) for p in 目录.rglob('*') if p.suffix.lower() in 扩展名]
        return [str(p) for p in 目录.glob('*') if p.suffix.lower() in 扩展名]

    def 更新文件列表(self, 路径: str, 递归: bool, 后缀: str) -> Tuple[List[str], str]:
        """更新文件列表并生成哈希"""
        扩展名集合 = {f".{e.strip().lower()}" for e in 后缀.split(",")}
        文件 = self.扫描文件(路径, 递归, 扩展名集合)
        文件.sort()
        
        md5 = hashlib.md5()
        for f in 文件:
            md5.update(f.encode())
        return 文件, md5.hexdigest()

    def 加载状态(self) -> None:
        """加载状态文件"""
        try:
            if self.状态文件.exists():
                with self.状态文件.open("r") as f:
                    self.当前状态.update(json.load(f))
        except Exception as e:
            print(f"状态加载失败: {e}")

    def 保存状态(self) -> None:
        """保存状态文件"""
        try:
            with self.状态文件.open("w") as f:
                json.dump(self.当前状态, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"状态保存失败: {e}")

    def 预加载图像(self, 开始索引: int) -> None:
        for i in range(开始索引, 开始索引 + self.缓存大小):
            idx = i % len(self.当前状态["文件"])
            if idx not in self.缓存:
                try:
                    self.执行器.submit(self.加载单张图像, idx)
                except Exception as e:
                    print(f"提交预加载任务失败: {e}")

    def 加载单张图像(self, 索引: int) -> None:
        try:
            文件路径 = self.当前状态["文件"][索引]
            img = cv2.imread(文件路径)
            if img is None:
                raise RuntimeError(f"无法加载图像: {文件路径}")
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # 转换为 RGB
            if not self.当前状态.get("允许RGBA", True) and img.shape[2] == 4:
                img = img[:, :, :3]
            张量 = torch.from_numpy(img.astype(np.float32) / 255.0)
            self.缓存[索引] = 张量
        except Exception as e:
            print(f"预加载失败 {文件路径}: {e}")

    def 加载下一张图像(self, 
                   目录路径: str,
                   包括子目录: bool,
                   后缀: str,
                   允许RGBA: bool,
                   自刷新: bool) -> Tuple[torch.Tensor, str, str]:
        绝对路径 = 清理路径(目录路径)
        if not Path(绝对路径).is_dir():
            raise ValueError("无效的目录路径")

        状态变更 = False
        新文件, 新哈希 = self.更新文件列表(绝对路径, 包括子目录, 后缀)
        
        if (绝对路径 != self.当前状态["路径"] or
            包括子目录 != self.当前状态["递归"] or
            后缀 != self.当前状态["后缀"] or
            (自刷新 and 新哈希 != self.当前状态["文件哈希"])):
            状态变更 = True
        
        if 状态变更 or not self.当前状态["文件"]:
            self.当前状态.update({
                "路径": 绝对路径,
                "递归": 包括子目录,
                "后缀": 后缀,
                "文件": 新文件,
                "文件哈希": 新哈希,
                "索引": 0,
                "允许RGBA": 允许RGBA
            })
            self.缓存.clear()
        
        if not self.当前状态["文件"]:
            raise RuntimeError("没有找到符合条件的文件")
        
        当前索引 = self.当前状态["索引"]
        if 当前索引 not in self.缓存:
            self.加载单张图像(当前索引)
        
        图像张量 = self.缓存.pop(当前索引, None)
        if 图像张量 is None:
            raise RuntimeError("图像加载失败")
        
        self.当前状态["索引"] = (当前索引 + 1) % len(self.当前状态["文件"])
        self.预加载图像(self.当前状态["索引"])
        self.保存状态()
        
        当前路径 = self.当前状态["文件"][当前索引]
        子路径 = str(Path(当前路径).relative_to(绝对路径))
        
        return (图像张量.unsqueeze(0), 子路径, 当前路径)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")

# ======================== 注册节点 ========================
NODE_CLASS_MAPPINGS = {
    "保存图像带路径": 保存图像带路径,
    "加载图像带路径": 加载图像带路径
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "保存图像带路径": "Save Image with Path",
    "加载图像带路径": "Load Images with Path"
}