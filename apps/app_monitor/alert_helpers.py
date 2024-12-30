from typing import List, Dict, Union

from apps.app_monitor.apiviews.monitor_views import UnitAdminEmailViewSet
from apps.app_monitor.managers import MonitorWebsiteManager


class AlertEmailsHelper:
    @staticmethod
    def get_website_user_emails(url_hash: str) -> List[str]:
        """
        站点监控用户邮箱查询
        """
        emails = MonitorWebsiteManager.get_site_user_emails(url_hash=url_hash)
        return [e['email'] for e in emails]

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
        unit = UnitAdminEmailViewSet.try_get_unit(unit_tag)
        if not unit:
            return None

        emails = UnitAdminEmailViewSet.get_unit_emails(unit)
        return {
            'tag': unit_tag,
            'unit': {
                'name': unit.name, 'name_en': unit.name_en
            },
            'emails': emails
        }
