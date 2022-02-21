#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import lib
import json
from datetime import datetime, timedelta


# datetime序列化
class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return json.JSONEncoder.default(self, obj)


# 把 "/" 替换成 "_"
def transfer_character(string):
    return "_".join(string.split("/"))


