class VerifyUtils:
    @staticmethod
    def is_blank_string(val : str) -> bool:
        if val is None:
            return True
        if val == '':
            return True
        if val.isspace():
            return True
        return False

    @staticmethod
    def is_empty_list(val : list) -> bool:
        if val is None:
            return True
        if len(list) == 0:
            return True
        return False