from enum import Enum

class BusinessErrorType(str, Enum):
    """业务状态常量"""
    BUSINESS_ERROR = "BUSINESS_ERROR"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"

class BusinessErrorInformation(str, Enum):
    """业务信息常量"""
    DEPENDS_SUGGEST = "depends=true时，forecast不能为空"
    DEPENDS_SUMMARY = "depends=true时，forecast和suggestion不能为空"
    DEPENDS_BRIEF = "depends=true时，forecast, suggestion和summary不能为空"