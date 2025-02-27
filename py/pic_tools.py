import vtracer
import tempfile
import os
import folder_paths
from wand.image import Image as WandImage
from PIL import Image as PILImage
import torch
import numpy as np
import io

class PIC2SVG:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "colormode": (["color", "binary"], {"default": "color"}),
                "hierarchical": (["stacked", "cutout"], {"default": "stacked"}),
                "mode": (["spline", "polygon", "none"], {"default": "spline"}),
                "filter_speckle": ("INT", {"default": 4, "min": 1, "max": 128, "step": 1}),
                "color_precision": ("INT", {"default": 6, "min": 1, "max": 10, "step": 1}),
                "layer_difference": ("INT", {"default": 16, "min": 1, "max": 20, "step": 1}),
                "corner_threshold": ("INT", {"default": 60, "min": 1, "max": 100, "step": 1}),
                "length_threshold": ("FLOAT", {"default": 4.0, "min": 3.5, "max": 10.0, "step": 0.1}),
                "max_iterations": ("INT", {"default": 10, "min": 1, "max": 20, "step": 1}),
                "splice_threshold": ("INT", {"default": 45, "min": 1, "max": 100, "step": 1}),
                "path_precision": ("INT", {"default": 8, "min": 1, "max": 10, "step": 1}),
                "svg_output_directory": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("图像",)
    FUNCTION = "process_image"
    CATEGORY = "pic_tools"

    def process_image(self, **kwargs):
        # 参数解包
        image = kwargs['image']
        svg_output_directory = kwargs['svg_output_directory']
        colormode = kwargs['colormode']
        hierarchical = kwargs['hierarchical']
        mode = kwargs['mode']
        filter_speckle = kwargs['filter_speckle']
        color_precision = kwargs['color_precision']
        layer_difference = kwargs['layer_difference']
        corner_threshold = kwargs['corner_threshold']
        length_threshold = kwargs['length_threshold']
        max_iterations = kwargs['max_iterations']
        splice_threshold = kwargs['splice_threshold']
        path_precision = kwargs['path_precision']

        try:
            # 图像预处理
            if len(image.shape) == 4:
                image = image.squeeze(0)
            image_array = (image.numpy().squeeze() * 255).astype(np.uint8)
            pil_image = PILImage.fromarray(image_array)

            # 设置输出路径
            svg_output_directory = svg_output_directory or folder_paths.get_output_directory()
            os.makedirs(svg_output_directory, exist_ok=True)
            
            # 生成唯一文件名
            base_filename = f"vector_{hash(pil_image.tobytes()):x}"
            svg_path = os.path.join(svg_output_directory, f"{base_filename}.svg")

            # 矢量转换
            with tempfile.NamedTemporaryFile(suffix=".png") as tmp_img:
                pil_image.save(tmp_img.name)
                vtracer.convert_image_to_svg_py(
                    tmp_img.name, svg_path,
                    colormode=colormode,
                    hierarchical=hierarchical,
                    mode=mode,
                    filter_speckle=filter_speckle,
                    color_precision=color_precision,
                    layer_difference=layer_difference,
                    corner_threshold=corner_threshold,
                    length_threshold=length_threshold,
                    max_iterations=max_iterations,
                    splice_threshold=splice_threshold,
                    path_precision=path_precision
                )

            # 格式转换
            with WandImage(filename=svg_path) as wand_img:
                png_buffer = wand_img.make_blob('png')
                output_image = PILImage.open(io.BytesIO(png_buffer)).convert('RGB')

            # 张量转换
            # tensor_image = torch.from_numpy(np.array(output_image)).float() / 255.0
            # tensor_image = tensor_image.unsqueeze(0)  # 添加批次维度
            
            # 将 PIL 图像转换为 torch tensor
            tensor_image = torch.from_numpy(np.array(output_image)).permute(2, 0, 1).float() / 255.0  

            return (tensor_image,)
        except Exception as e:
            print(f"处理过程中发生错误: {str(e)}")
            return (torch.zeros(1, 1, 1, 3),)  # 返回空张量保持流程

NODE_CLASS_MAPPINGS = {"PIC2SVG": PIC2SVG}
NODE_DISPLAY_NAME_MAPPINGS = {"PIC2SVG": "PIC TO SVG"}
