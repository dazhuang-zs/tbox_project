"""
图片尺寸信息处理工具
"""

import re
from typing import List


def check_aspect_ratio(ratios: List, width: int, height: int) -> dict:
    """检查图片宽高比是否在工具1要求的比例范围内"""
    # 计算当前宽高比
    current_ratio = width / height

    # 检查每个预定义比例
    for ratio in ratios:
        w, h = map(int, ratio.split(':'))
        target_ratio = w / h
        # 允许小的误差（0.05）
        if abs(current_ratio - target_ratio) < 0.05:
            return {
                'is_match': True,
                'matched_ratio': ratio,
                'current_ratio': round(current_ratio, 2)
            }
    return {
        'is_match': False,
        'matched_ratio': None,
        'current_ratio': round(current_ratio, 2)
    }


def get_image_size(image_info: dict) -> dict:
    """根据输入图片尺寸信息获取模型需要的图片尺寸信息"""
    # 正则检验尺寸必须是"2048x2048" 这种形式
    regex = r'^(\d+)[xX](\d+)$'
    use_tool1 = False
    # 工具1要的数据格式
    default_image_config = {
        "image_size": '2K',
    }

    image_config = default_image_config
    radio = image_info.get('radio') or ''
    image_size: str = (image_info.get('image_size') or
                      default_image_config.get('image_size') or '2K')
    match = re.match(regex, radio)
    ratios = ['9:16', '2:3', '3:4', '4:5', '1:1', '5:4', '4:3', '3:2', '16:9']

    if match:
        width = int(match.group(1))
        height = int(match.group(2))
        data = check_aspect_ratio(ratios, width, height)
        # 获取工具1需要的尺寸信息
        if data.get('is_match') and data.get('matched_ratio'):
            use_tool1 = True
            image_config = {
                'aspect_ratio': data.get('matched_ratio'),
                'image_size': default_image_config.get('image_size')
            }
            image_size = radio or image_size
        else:
            use_tool1 = False
            image_size = radio or image_size
    else:
        use_tool1 = True
        image_config = default_image_config
    return {
        'use_tool1': use_tool1,
        'image_size': image_size,
        'image_config': image_config
    }


if __name__ == '__main__':
    import sys
    import json

    if len(sys.argv) < 2:
        print(json.dumps({'error': 'Usage: python3 get_size.py \'{"radio":"2048x2048","image_size":"2K"}\''}))
        sys.exit(1)

    try:
        image_info = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({'error': f'Invalid JSON: {e}'}))
        sys.exit(1)

    print(json.dumps(get_image_size(image_info)))