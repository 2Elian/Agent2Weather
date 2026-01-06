class BusinessError(Exception):
    """业务规则错误（客户端参数合法，但业务条件不满足）"""
    def __init__(self, message: str, code: str = "BUSINESS_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class DependencyError(BusinessError):
    """依赖条件不满足"""
    def __init__(self, message: str):
        super().__init__(message, code="DEPENDENCY_ERROR")