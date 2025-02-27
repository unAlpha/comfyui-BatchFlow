import os
import platform
import numpy as np
from PIL import Image
import torch
import json

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
    高级图像序列加载器
    功能特性：
    - 支持递归/非递归目录扫描
    - 跨会话状态持久化
    - 智能文件变更检测
    - 自动索引循环
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
        """加载持久化状态"""
        try:
            if os.path.exists(self.状态文件):
                with open(self.状态文件, 'r') as f:
                    self.当前状态 = json.load(f)
                    # 路径兼容性处理
                    self.当前状态["路径"] = os.path.normpath(self.当前状态["路径"])
        except Exception as e:
            print(f"状态加载失败: {str(e)}")

    def _保存状态(self):
        """保存当前状态"""
        try:
            with open(self.状态文件, 'w') as f:
                json.dump(self.当前状态, f, indent=2)
        except Exception as e:
            print(f"状态保存失败: {str(e)}")

    def _生成文件列表(self, 路径, 递归,后缀):
        """生成规范化路径的文件列表"""
        文件列表 = []
        try:
            if 递归:
                for 根目录, _, 文件 in os.walk(路径):
                    文件.sort()
                    文件列表.extend([os.path.normpath(os.path.join(根目录, f)) for f in 文件])
            else:
                for f in sorted(os.listdir(路径)):
                    完整路径 = os.path.normpath(os.path.join(路径, f))
                    if os.path.isfile(完整路径):
                        文件列表.append(完整路径)
            
                        # 扩展名过滤（保留路径规范化）
            有效扩展名 = set(ext.strip().lower() for ext in 后缀.split(','))
            过滤后的文件 = [
                f for f in 文件列表
                if os.path.splitext(f)[1][1:].lower() in 有效扩展名
            ]
            
        except PermissionError:
            print("错误：没有目录访问权限")
        return 过滤后的文件

    def _验证状态(self, 当前路径, 当前递归, 后缀, 允许RGBA, 自刷新):
        """带递归检测的状态验证"""
        保存的路径 = self.当前状态.get("路径", "")
        保存的递归 = self.当前状态.get("递归", False)
        保存的自刷新 = self.当前状态.get("刷新", False)
        保存的后缀 = self.当前状态.get("后缀", "")
        保存的RGBA= self.当前状态.get("RGBA", True)

        if 后缀 != 保存的后缀:
            return True, []
        
        if 允许RGBA != 保存的RGBA:
            return True, []
        
        if 自刷新 != 保存的自刷新:
            return True , []

        if 当前路径 != 保存的路径:
            return True , []
        
        if 保存的递归 != 当前递归:
            return True, []
        
        if 自刷新:
            临时文件列表 = self._生成文件列表(当前路径, 当前递归, 后缀)
            if 临时文件列表 != self.当前状态.get("文件列表"):
                print(f"{临时文件列表}\n\n----{self.当前状态.get("文件列表")}")
                return True, 临时文件列表
        
        return False, []

    def load_next_image(self, 目录路径, 包括子目录, 后缀, 允许RGBA, 自刷新):
        # 输入预处理
       
        绝对路径 = os.path.normpath(os.path.abspath(目录路径))
        
        # 异常情况处理
        if not os.path.exists(绝对路径):
            raise ValueError(f"路径不存在: {绝对路径}")
        if not os.path.isdir(绝对路径):
            raise ValueError("必须选择目录")

        # 状态决策逻辑
        是否刷新, 检测文件列表 = self._验证状态(绝对路径, 包括子目录, 后缀, 允许RGBA,自刷新)
        if 是否刷新:
            当前文件列表 = 检测文件列表 if 检测文件列表 else self._生成文件列表(绝对路径, 包括子目录, 后缀)
    
            # 更新状态
            self.当前状态 = {
                "路径": 绝对路径,
                "递归": 包括子目录,
                "文件列表": 当前文件列表,
                "索引": 0,
                "刷新": 自刷新,
                "后缀": 后缀,
                "RGBA": 允许RGBA,
            }
        else:
            print("状态验证通过，复用文件列表")

        # 处理空目录
        if not self.当前状态["文件列表"]:
            raise RuntimeError("目录中没有符合条件的文件")

        # 加载当前图像
        当前索引 = self.当前状态["索引"]
        当前文件 = self.当前状态["文件列表"][当前索引]

        子路径 = os.path.relpath(当前文件, 绝对路径)

        try:
            图像 = Image.open(当前文件)
            if not 允许RGBA and 图像.mode == 'RGBA':
                图像 = 图像.convert("RGB")
        except Exception as e:
            raise IOError(f"无法加载图像: {当前文件} - {str(e)}")

        # 转换为 ComfyUI 兼容格式
        图像数组 = np.array(图像.convert("RGB")).astype(np.float32) / 255.0
        图像张量 = torch.from_numpy(图像数组)[None,]

        # 更新索引（循环逻辑）
        self.当前状态["索引"] = (当前索引 + 1) % len(self.当前状态["文件列表"])
        self._保存状态()

        return (图像张量, 子路径, 当前文件, )

NODE_CLASS_MAPPINGS = {
    "SaveImageWithPath": SaveImageWithPath,
    "LoadImageWithPath": LoadImageWithPath
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveImageWithPath": "Save Image with Path",
    "LoadImageWithPath": "Load Images with Path"
}