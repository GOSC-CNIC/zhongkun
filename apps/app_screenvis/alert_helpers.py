from typing import List, Dict, Union

from utils.alert_helper import AlertEmailsHelperBase


class AlertEmailsHelper(AlertEmailsHelperBase):
    @staticmethod
    def get_website_user_emails(url_hash: str) -> List[str]:
        """
        站点监控用户邮箱查询
        """
        return []

    @staticmethod
    def get_monitor_unit_user_emails(unit_tag: str) -> Union[Dict[str, Union[str, List, Dict]], None]:
        """
        查询监控单元管理员用户的邮件地址
        :return: {
            "tag": "xx",
            "unit": {"name": "xx", "name_en": "xxx"},
            "emails": ["xxx@cnic.cn"]
        }
        or None
        """
        return None
