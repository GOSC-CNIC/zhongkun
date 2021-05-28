
class Encrypter(object):
    class InvlidEncrypted(Exception):
        pass

    def __init__(self, key: str):
        self.key = key          # 密钥
        self.delimiter = 'x'    # 字符加密分隔符; not in [0-9,a-e]
        self.prefix = '#'      # 加密后字符串开头标志; not in [0-9,a-e]

    def _key_char(self, index: int):
        length = len(self.key)
        i = index % length
        return self.key[i]

    @staticmethod
    def _unicode_to_hex(code: int) -> str:
        hex_code = hex(code).lower()
        return hex_code.lstrip('0x')

    @staticmethod
    def _hex_to_unicode(h: str):
        return int(h, 16)

    def encrypt(self, text: str):
        """
        加密字符串
        """
        items = []
        for i, v in enumerate(text):
            kv = self._key_char(i)
            code = ord(v) + ord(kv)     # 加密字符 = 字符的Unicode码 + 秘钥的Unicode码
            items.append(self._unicode_to_hex(code))

        return self.prefix + self.delimiter.join(items)

    def decrypt(self, encrypted: str):
        """
        解密一个加密的字符串

        :raises: InvlidEncrypted
        """
        items = []
        if not encrypted.startswith(self.prefix):
            raise self.InvlidEncrypted()

        encrypted = encrypted.lstrip(self.prefix)
        if not encrypted:
            return ''

        code_list = encrypted.split(self.delimiter)
        for i, h in enumerate(code_list):
            kv = self._key_char(i)
            try:
                # 解密字符 = (加密字符Unicode码 - 秘钥字符的Unicode码)的字符
                code = self._hex_to_unicode(h)
                item = chr(code - ord(kv))
            except Exception as e:
                raise self.InvlidEncrypted(str(e))

            items.append(item)

        return ''.join(items)

    def is_encrypted(self, s: str):
        """
        是否是加密后的字符串
        """
        try:
            self.decrypt(s)
        except self.InvlidEncrypted:
            return False

        return True


if __name__ == "__main__":
    def test(text):
        encrypter = Encrypter(key="""!2#$fk*76/';:""")
        encypted = encrypter.encrypt(text)
        print(f"*Encypt text: {text} => {encypted}")
        raw_text = encrypter.decrypt(encypted)
        print(f"*Decypt: {encypted} => {raw_text}")
        if text == raw_text:
            print('[Ok] Encypt/Decypt text')
        else:
            print('[Failed] Encypt/Decypt text')


    text1 = 'iefaba!@#4567$%&^&?<<adJGKKkhafoewgfieuq:"{}HHV'
    text2 = 'iefaba!@#4567$%&^&?<<adJGK发hi发fieuq:"{}HHV'
    text3 = ''
    text4 = '哈'
    print('---------text1-----------')
    test(text1)
    print('---------text2-----------')
    test(text2)
    print('---------text3-----------')
    test(text3)
    print('---------text4-----------')
    test(text4)
