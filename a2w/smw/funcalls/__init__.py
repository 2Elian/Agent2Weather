from typing import List
TOOLS: List = []
def register_tool(fn):
    TOOLS.append(fn)
    return fn

from . import db_function_call