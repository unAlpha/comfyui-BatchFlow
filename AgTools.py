import os
import platform
import numpy as np
from PIL import Image
import torch
import json

class SaveImageWithPath:
    """
    SaveImageWithPath 是一个 ComfyUI 节点，用于将图像保存到指定路径。
    新增功能：当custom_path为文件夹时，将图片输出到该文件夹。
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "图像": ("IMAGE",),
                "output_dir": ("STRING", {"default": "output", "display_name": "默认输出目录"},),
                "filename_prefix": ("STRING", {"default": "output", "display_name": "文件名前缀"}),
                "filename_suffix": ("STRING", {"default": "", "display_name": "文件名后缀"}),
                "apply_suffix_custom_path": ("BOOLEAN", {"default": False,"display_name": "应用后缀到自定义路径"}),
                "custom_path": ("STRING", {"default": "","display_name": "自定义路径"}),
            },
        }

    FUNCTION = "save_image_with_path"
    CATEGORY = "Agtools"
    OUTPUT_NODE = True

    RETURN_TYPES = ()
    RETURN_NAMES = ()

    def save_image_with_path(self, 图像, filename_prefix="", filename_suffix="", output_dir="output", custom_path="", apply_suffix_custom_path=False):
        try:
            print(f"DEBUG: Input - filename_prefix: '{filename_prefix}', filename_suffix: '{filename_suffix}', output_dir: '{output_dir}', custom_path: '{custom_path}'")

            # 处理 custom_path 为目录的情况
            if custom_path:
                is_directory = False

                # 检查是否存在的目录
                if os.path.isdir(custom_path):
                    is_directory = True
                else:
                    # 分解路径
                    dir_part, file_part = os.path.split(custom_path)
                    
                    # 判断是否为目录格式（文件名部分为空或没有扩展名）
                    if not file_part:
                        is_directory = True
                    else:
                        _, ext = os.path.splitext(file_part)
                        if not ext:
                            is_directory = True

                if is_directory:
                    # 设置为输出目录并清空 custom_path
                    output_dir = custom_path
                    custom_path = ""
                    print(f"DEBUG: Custom path identified as directory. New output_dir: {output_dir}")

            # 处理文件路径或自动生成路径
            if custom_path:
                # 处理完整文件路径
                directory, filename = os.path.split(os.path.abspath(custom_path))
                name, ext = os.path.splitext(filename)
                
                # 应用后缀（如果启用）
                if apply_suffix_custom_path and filename_suffix:
                    modified_filename = f"{name}{filename_suffix}{ext}"
                else:
                    modified_filename = filename
                
                full_path = os.path.join(directory, modified_filename)
                print(f"DEBUG: Using custom file path: {full_path}")
            else:
                # 自动生成文件名
                if not output_dir:
                    output_dir = "output"
                
                os.makedirs(output_dir, exist_ok=True)
                print(f"DEBUG: Generating filename in directory: {output_dir}")

                # 查找可用文件名
                counter = 1
                while True:
                    filename = f"{filename_prefix}_{counter:05}{filename_suffix}.png"
                    full_path = os.path.join(output_dir, filename)
                    if not os.path.exists(full_path):
                        break
                    counter += 1
                print(f"DEBUG: Generated new file path: {full_path}")

            # 处理中文路径（Windows特殊处理）
            def encode_path(path):
                if platform.system() == "Windows":
                    try:
                        return path.encode('utf-8').decode('mbcs')
                    except:
                        return path
                return path
            
            full_path = encode_path(full_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            # 保存图像
            img_tensor = 图像.cpu().numpy()
            img_array = np.clip(255. * img_tensor.squeeze(), 0, 255).astype(np.uint8)
            Image.fromarray(img_array).save(full_path)
            print(f"DEBUG: Image saved successfully to: {full_path}")

        except Exception as e:
            print(f"ERROR: Failed to save image. Reason: {str(e)}")
            raise

        return ()

    @classmethod
    def IS_CHANGED(cls, image, **kwargs):
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
        self.state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "comfy_agtools_state.json")
        self.current_state = {
            "path": "",
            "recursive": False,
            "file_list": [],
            "index": 0
        }
        self._load_state()

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "path": ("STRING", {"default": "./input", "directory": True,"display_name": "目录路径"}),
                "recursive": ("BOOLEAN", {"default": True,"display_name": "包括子目录"}),
                "extensions": ("STRING", {"default": "jpg,png,jpeg,webp","display_name": "后缀"}),
                "allow_RGBA": ("BOOLEAN", {"default": True,"display_name": "充许RGBA"}),
                "reset_counter": ("BOOLEAN", {"default": False,"display_name": "自重置"}),
            }
        }
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return float("nan")
    
    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("图像", "当前路径")
    FUNCTION = "load_next_image"

    CATEGORY = "Agtools"

    def _load_state(self):
        """加载持久化状态"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    self.current_state = json.load(f)
                    # 路径兼容性处理
                    self.current_state["path"] = os.path.normpath(self.current_state["path"])
        except Exception as e:
            print(f"状态加载失败: {str(e)}")

    def _save_state(self):
        """保存当前状态"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.current_state, f, indent=2)
        except Exception as e:
            print(f"状态保存失败: {str(e)}")

    def _generate_file_list(self, path, recursive):
        """生成规范化路径的文件列表"""
        file_list = []
        try:
            if recursive:
                for root, _, files in os.walk(path):
                    files.sort()
                    file_list.extend([os.path.normpath(os.path.join(root, f)) for f in files])
            else:
                for f in sorted(os.listdir(path)):
                    full_path = os.path.normpath(os.path.join(path, f))
                    if os.path.isfile(full_path):
                        file_list.append(full_path)
        except PermissionError:
            print("错误：没有目录访问权限")
        return file_list

    def _validate_state(self, current_path, current_recursive):
        """带递归检测的状态验证"""
        saved_path = self.current_state.get("path", "")
        saved_recursive = self.current_state.get("recursive", False)
        
        # 路径标准化比较
        if os.path.normpath(saved_path) != os.path.normpath(current_path):
            return False
        
        if saved_recursive != current_recursive:
            return False
        
        # 文件存在性验证
        return all(os.path.exists(f) for f in self.current_state["file_list"])

    def load_next_image(self, path, recursive, extensions, allow_RGBA, reset_counter):
        # 输入预处理
        valid_exts = set(ext.strip().lower() for ext in extensions.split(','))
        abs_path = os.path.normpath(os.path.abspath(path))
        
        # 异常情况处理
        if not os.path.exists(abs_path):
            raise ValueError(f"路径不存在: {abs_path}")
        if not os.path.isdir(abs_path):
            raise ValueError("必须选择目录")

        # 状态决策逻辑
        if reset_counter or not self._validate_state(abs_path, recursive):
            current_files = self._generate_file_list(abs_path, recursive)
            
            # 扩展名过滤（保留路径规范化）
            filtered_files = [
                f for f in current_files
                if os.path.splitext(f)[1][1:].lower() in valid_exts
            ]
            
            # 更新状态
            self.current_state = {
                "path": abs_path,
                "recursive": recursive,
                "file_list": filtered_files,
                "index": 0
            }
        else:
            print("状态验证通过，复用文件列表")

        # 处理空目录
        if not self.current_state["file_list"]:
            raise RuntimeError("目录中没有符合条件的文件")

        # 加载当前图像
        current_index = self.current_state["index"]
        current_file = self.current_state["file_list"][current_index]
        
        try:
            image = Image.open(current_file)
            if not allow_RGBA and image.mode == 'RGBA':
                image = image.convert("RGB")
        except Exception as e:
            raise IOError(f"无法加载图像: {current_file} - {str(e)}")

        # 更新索引（循环逻辑）
        self.current_state["index"] = (current_index + 1) % len(self.current_state["file_list"])
        self._save_state()

        # 转换为ComfyUI兼容格式
        image_np = np.array(image.convert("RGB")).astype(np.float32) / 255.0
        image_tensor = torch.from_numpy(image_np)[None,]

        return (image_tensor, current_file)

NODE_CLASS_MAPPINGS = {
    "SaveImageWithPath": SaveImageWithPath,
    "LoadImageWithPath": LoadImageWithPath
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SaveImageWithPath": "Save Image with Path",
    "LoadImageWithPath": "Load Images with Path"
}
