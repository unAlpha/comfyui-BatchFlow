import importlib.util
import glob
import os
import sys
from concurrent.futures import ThreadPoolExecutor

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

def load_module(file_path):
    module_name = os.path.splitext(os.path.basename(file_path))[0]
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return (
            getattr(module, "NODE_CLASS_MAPPINGS", None),
            getattr(module, "NODE_DISPLAY_NAME_MAPPINGS", None)
        )
    except Exception as e:
        print(f"Error in {file_path}: {str(e)}")
        return (None, None)

def main():
    py_dir = os.path.join(os.path.dirname(__file__), "py")
    files = [f for f in glob.glob(os.path.join(py_dir, "*.py")) 
            if not f.endswith("__init__.py")]

    # 并行加载（I/O密集型场景使用线程池更优）
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(load_module, files)

    # 合并结果
    for class_mappings, display_mappings in results:
        if class_mappings:
            NODE_CLASS_MAPPINGS.update(class_mappings)
        if display_mappings:
            NODE_DISPLAY_NAME_MAPPINGS.update(display_mappings)

main()

WEB_DIRECTORY = "./web"
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
