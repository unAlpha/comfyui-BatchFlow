import os
import platform
import numpy as np
from PIL import Image
import torch
import json
import hashlib

class SaveImageWithPath:
    """
    SaveImageWithPath 是一个 ComfyUI 节点，用于将图像保存到指定路径。
    新增功能：当自定义路径为文件夹时，将图片输出到该文件夹。
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
                "子路径": ("STRING",{"forceInput": True}),
            },
        }

    FUNCTION = "save_image_with_path"
    CATEGORY = "batch_flow"
    OUTPUT_NODE = True

    RETURN_TYPES = ()
    RETURN_NAMES = ()

    def save_image_with_path(self, 图像, 文件名前缀="", 文件名后缀="", 默认输出目录="output", 自定义路径="", 应用后缀到自定义路径=False, 子路径=""):
        try:
            print(f"DEBUG: 输入 - 文件名前缀: '{文件名前缀}', 文件名后缀: '{文件名后缀}', 默认输出目录: '{默认输出目录}', 自定义路径: '{自定义路径}'")
            # 处理子路径合并
            子路径 = 子路径 or ""

            if 子路径:
                if 自定义路径 and os.path.isdir(自定义路径):
                    基路径 = 自定义路径
                else:
                    基路径 = 默认输出目录
                新自定义路径 = os.path.join(基路径, 子路径)
                print(f"DEBUG: 应用子路径后的新自定义路径: {新自定义路径}")
                自定义路径 = 新自定义路径

            # 处理 自定义路径 为目录的情况
            if 自定义路径:
                是目录 = False

                # 检查是否为已存在的目录
                if os.path.isdir(自定义路径):
                    是目录 = True
                else:
                    # 分解路径
                    目录部分, 文件部分 = os.path.split(自定义路径)
                    
                    # 判断是否为目录格式（文件名部分为空或没有扩展名）
                    if not 文件部分:
                        是目录 = True
                    else:
                        _, 扩展名 = os.path.splitext(文件部分)
                        if not 扩展名:
                            是目录 = True

                if 是目录:
                    # 设置为输出目录并清空 自定义路径
                    默认输出目录 = 自定义路径
                    自定义路径 = ""
                    print(f"DEBUG: 自定义路径 被识别为目录。新默认输出目录: {默认输出目录}")

            # 处理文件路径或自动生成路径
            if 自定义路径:
                # 处理完整文件路径
                目录, 文件名 = os.path.split(os.path.abspath(自定义路径))
                名称, 扩展名 = os.path.splitext(文件名)
                
                # 应用后缀（如果启用）
                if 应用后缀到自定义路径 and 文件名后缀:
                    修改后的文件名 = f"{名称}{文件名后缀}{扩展名}"
                else:
                    修改后的文件名 = 文件名
                
                完整路径 = os.path.join(目录, 修改后的文件名)
                print(f"DEBUG: 使用自定义文件路径: {完整路径}")
            else:
                # 自动生成文件名
                if not 默认输出目录:
                    默认输出目录 = "output"
                
                os.makedirs(默认输出目录, exist_ok=True)
                print(f"DEBUG: 在目录中生成文件名: {默认输出目录}")

                # 查找可用文件名
                计数器 = 1
                while True:
                    文件名 = f"{文件名前缀}_{计数器:05}{文件名后缀}.png"
                    完整路径 = os.path.join(默认输出目录, 文件名)
                    if not os.path.exists(完整路径):
                        break
                    计数器 += 1
                print(f"DEBUG: 生成的新文件路径: {完整路径}")

            # 处理中文路径（Windows特殊处理）
            def 编码路径(路径):
                if platform.system() == "Windows":
                    try:
                        return 路径.encode('utf-8').decode('mbcs')
                    except:
                        return 路径
                return 路径
            
            完整路径 = 编码路径(完整路径)
            os.makedirs(os.path.dirname(完整路径), exist_ok=True)

            # 保存图像
            图像张量 = 图像.cpu().numpy()
            图像数组 = np.clip(255. * 图像张量.squeeze(), 0, 255).astype(np.uint8)
            Image.fromarray(图像数组).save(完整路径)
            print(f"DEBUG: 图像成功保存到: {完整路径}")

        except Exception as e:
            print(f"错误: 保存图像失败。原因: {str(e)}")
            raise

        return ()

    @classmethod
    def IS_CHANGED(cls, 图像, **kwargs):
        return float('nan')

class LoadImageWithPath:
    """
    高级图像序列加载器(优化版)
    速度优化点：
    - 边扫描边过滤文件扩展名
    - 使用os.scandir提升文件检测速度
    - 哈希指纹快速验证文件列表变更
    - 图像转换流程优化
    """
    
    def __init__(self):
        self.状态文件 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tmp_file_state.json")
        self.当前状态 = {
            "路径": "",
            "递归": False,
            "文件列表": [],
            "索引": 0,
            "刷新": False,
            "后缀": "",
            "RGBA": True,
            "文件列表_hash": "",
        }
        self._加载状态()

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

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")
    
    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("图像", "子路径", "当前路径")
    FUNCTION = "load_next_image"

    CATEGORY = "batch_flow"

    def _加载状态(self):
        """加载持久化状态(带向后兼容)"""
        try:
            if os.path.exists(self.状态文件):
                with open(self.状态文件, 'r') as f:
                    载入状态 = json.load(f)
                    # 兼容旧版状态文件
                    self.当前状态 = {**self.当前状态, **载入状态}
                    self.当前状态["路径"] = os.path.normpath(self.当前状态["路径"])
        except Exception as e:
            print(f"状态加载失败: {str(e)}")

    def _保存状态(self):
        """保存当前状态(含文件列表哈希)"""
        try:
            with open(self.状态文件, 'w') as f:
                json.dump(self.当前状态, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"状态保存失败: {str(e)}")

    def _生成文件列表(self, 路径, 递归, 后缀, **其他参数):
        """高效生成规范化文件列表"""
        有效扩展名 = {ext.strip().lower() for ext in 后缀.split(',')}
        有效扩展名带点 = {f".{ext}" for ext in 有效扩展名}
        文件列表 = []

        if 递归:
            for 根目录, _, 文件 in os.walk(路径):
                # 先过滤后排序提升性能
                匹配文件 = sorted(
                    f for f in 文件
                    if os.path.splitext(f)[1].lower() in 有效扩展名带点
                )
                文件列表.extend(
                    os.path.normpath(os.path.join(根目录, f)) for f in 匹配文件
                )
        else:
            with os.scandir(路径) as entries:
                匹配文件 = sorted(
                    entry.path for entry in entries
                    if entry.is_file()
                    and os.path.splitext(entry.name)[1].lower() in 有效扩展名带点
                )
                文件列表.extend(os.path.normpath(p) for p in 匹配文件)

        return 文件列表

    def _验证状态(self, 当前参数):
        """智能状态验证(带哈希指纹验证)"""
        保存状态 = self.当前状态
        
        # 参数变更检查
        参数变更 = any(
            当前参数[k] != 保存状态[k]
            for k in ["路径", "递归", "后缀", "RGBA", "刷新"]
        )
        if 参数变更:
            新列表 = self._生成文件列表(**当前参数)
            新哈希 = self._计算列表哈希(新列表)
            return True, 新列表, 新哈希
        
        # 自刷新模式检查
        if 当前参数["刷新"]:
            新列表 = self._生成文件列表(**当前参数)
            新哈希 = self._计算列表哈希(新列表)
            if 新哈希 != 保存状态["文件列表_hash"]:
                return True, 新列表, 新哈希
        
        return False, None, None

    def _计算列表哈希(self, 文件列表):
        """快速计算文件列表指纹"""
        return hashlib.md5(",".join(文件列表).encode()).hexdigest()

    def load_next_image(self, 目录路径, 包括子目录, 后缀, 允许RGBA, 自刷新):
        # 输入预处理
        绝对路径 = os.path.normpath(os.path.abspath(目录路径))
        if not os.path.isdir(绝对路径):
            raise ValueError("必须选择有效目录")

        # 构造验证参数
        验证参数 = {
            "路径": 绝对路径,
            "递归": 包括子目录,
            "后缀": 后缀,
            "RGBA": 允许RGBA,
            "刷新": 自刷新,
        }

        # 执行状态验证
        需要刷新, 新列表, 新哈希 = self._验证状态(验证参数)
        if 需要刷新:
            self.当前状态.update({
                **验证参数,
                "文件列表": 新列表,
                "文件列表_hash": 新哈希,
                "索引": 0  # 重置索引
            })

        # 检查空列表
        if not self.当前状态["文件列表"]:
            raise RuntimeError("目录中没有符合条件的文件")

        # 加载当前图像
        当前索引 = self.当前状态["索引"]
        当前文件 = self.当前状态["文件列表"][当前索引]
        
        try:
            with Image.open(当前文件) as 图像:
                if not 允许RGBA and 图像.mode == 'RGBA':
                    图像 = 图像.convert("RGB")
                图像数组 = np.array(图像).astype(np.float32) / 255.0
        except Exception as e:
            raise IOError(f"图像加载失败: {当前文件} - {str(e)}")

        # 更新索引并保存状态
        self.当前状态["索引"] = (当前索引 + 1) % len(self.当前状态["文件列表"])
        self._保存状态()

        return (
            torch.from_numpy(图像数组)[None,],
            os.path.relpath(当前文件, 绝对路径),
            当前文件
        )

NODE_CLASS_MAPPINGS = {
    "SaveImageWithPath": SaveImageWithPath,
    "LoadImageWithPath": LoadImageWithPath
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveImageWithPath": "Save Image with Path",
    "LoadImageWithPath": "Load Images with Path"
}