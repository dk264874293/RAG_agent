'''
Author: 汪培良 rick_wang@yunquna.com
Date: 2026-01-06 07:48:05
LastEditors: 汪培良 rick_wang@yunquna.com
LastEditTime: 2026-01-06 07:48:07
FilePath: /RAG_agent/src/extensions/storage/storage_type.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
'''
from enum import StrEnum


class StorageType(StrEnum):
    ALIYUN_OSS = "aliyun-oss"
    AZURE_BLOB = "azure-blob"
    BAIDU_OBS = "baidu-obs"
    CLICKZETTA_VOLUME = "clickzetta-volume"
    GOOGLE_STORAGE = "google-storage"
    HUAWEI_OBS = "huawei-obs"
    LOCAL = "local"
    OCI_STORAGE = "oci-storage"
    OPENDAL = "opendal"
    S3 = "s3"
    TENCENT_COS = "tencent-cos"
    VOLCENGINE_TOS = "volcengine-tos"
    SUPABASE = "supabase"
