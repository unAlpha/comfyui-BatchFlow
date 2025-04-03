# ComfyUI-BatchFlow

ComfyUI-BatchFlow is an efficient batch processing extension designed for ComfyUI, providing enhanced image batch workflow functionality.

[中文文档](README_zh.md)

## Features

- **High-performance Batch Image Loading**: Smart indexing, cache preloading, parallel file scanning
- **Flexible Image Saving System**: Support for custom paths, subdirectory structures, and file naming
- **Image to SVG Conversion**: Integrated professional vectorization functionality with multiple conversion parameters
- **Intelligent Path Management**: Cross-platform compatibility, automatic path format handling

## Installation

### Method 1: Using ComfyUI Manager
1. Install [ComfyUI Manager](https://github.com/ltdrdata/ComfyUI-Manager) in ComfyUI
2. Search for "BatchFlow" in the manager search bar and install

### Method 2: Manual Installation
```bash
cd your_ComfyUI_directory/custom_nodes/
git clone https://github.com/username/comfyui-BatchFlow.git
cd comfyui-BatchFlow
pip install -r requirements.txt  # if there's a dependency file
```

## Main Components

### LoadImageWithPath
Optimized image loading node with the following features:
- Batch processing of local image folders
- Optional recursive scanning of subdirectories
- Support for multiple image formats
- Smart indexing and caching system for improved performance
- Custom index value to jump directly to specific images

### SaveImageWithPath
Enhanced image saving node with:
- Support for custom output paths and filename formats
- Automatic directory structure creation
- Smart indexing and file naming management
- Subdirectory parameter support for organized saving

### PIC2SVG Conversion
Provides advanced image to SVG conversion functionality:
- Support for color or binary mode
- Adjustable precision and detail control
- Custom output configuration

## Usage Examples

In ComfyUI, you can use these nodes to build efficient batch processing workflows:

1. Use the `LoadImageWithPath` node to load images from a specified directory
2. Connect to your image processing workflow
3. Use `SaveImageWithPath` to save the processed images, preserving the original directory structure if desired

## Advanced Configuration

Each node provides various parameters to meet different needs, such as:
- File format control
- Directory recursion options
- Output quality settings
- Cache and performance optimization

## License

[Please add your license information here]

## Contributing

Issues and improvement suggestions are welcome! Please participate through GitHub Issues or Pull Requests.

## Changelog

### v1.0.0
- Initial version released
- Implemented core batch image processing functionality
- Added SVG conversion tools
