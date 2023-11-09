class VerifyUtils:
    @staticmethod
    def is_blank_string(val: str) -> bool:
        """
        判断字符串是否为空
        """
        if val is None:
            return True
        if val == '':
            return True
        if val.isspace():
            return True
        return False

    @staticmethod
    def is_empty_list(val: list) -> bool:
        """
        判断列表是否为空
        """
        if val is None:
            return True
        if len(val) == 0:
            return True
        return False
    
    @staticmethod
    def string_to_bool(val: str) -> bool:
        """
        不区分大小写字符串转bool 无效字符串返回None
        """
        if val is None:
            return None
        val = val.lower()
        if val == 'true':
            return True
        elif val == 'false':
            return False
        else:
            return None