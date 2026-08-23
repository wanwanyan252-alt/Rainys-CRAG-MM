# 版权所有 (c) Meta Platforms, Inc. 及其关联公司。
# 保留所有权利。

# 本源代码依据本源代码树根目录下 LICENSE 文件中的
# 许可证进行授权。

"""请勿修改本文件。

本文件包含 ImageLoader 类，用于下载并缓存图像。
评测期间，缓存会被预先填充所有可用图像，一切都从缓存加载。
评测期间会禁用网络访问，使用不属于所提供数据集的图像 URL
会导致报错（所有 `requests.get` 调用都会失败）。
"""

import os
from hashlib import sha256
from io import BytesIO

import requests
from PIL import Image

CACHE_DIR = os.getenv(
    "CRAG_IMAGE_CACHE_DIR",
    os.path.join(os.path.expanduser("~"), ".cache/crag/", "image_cache"),
)
os.makedirs(CACHE_DIR, exist_ok=True)


class ImageLoader:
    def __init__(self, url: str):
        self.url = url

    def _get_cache_filename(self):
        file_ext = self.url.split(".")[-1].lower()
        return os.path.join(
            CACHE_DIR, sha256(self.url.encode()).hexdigest() + "." + file_ext
        )

    def _save_image_to_cache(self, image: Image.Image):
        image.save(self._get_cache_filename())

    def _load_image_from_cache(self):
        return Image.open(self._get_cache_filename())

    def _image_cache_exists(self):
        return os.path.exists(self._get_cache_filename())

    def download_image(self):
        headers = {"User-Agent": "CRAGBot/v0.0.1"}
        response = requests.get(self.url, stream=True, timeout=10, headers=headers)
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content))
            return image
        else:
            raise Exception(
                f"Failed to download image from {self.url}, status code:"
                f" {response.status_code}"
            )

    def get_image(self):
        if self._image_cache_exists():
            return self._load_image_from_cache()
        else:
            image = self.download_image()
            self._save_image_to_cache(image)
            return image
