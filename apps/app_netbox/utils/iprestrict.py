from utils.iprestrict import IPRestrictor, load_allowed_ips


class LinkIPRestrictor(IPRestrictor):
    SETTING_KEY_NAME = 'API_IPRESTRICT_LINK_ALLOWED_IPS'
    _allowed_ip_rules = load_allowed_ips(SETTING_KEY_NAME)

    def reload_ip_rules(self):
        self.allowed_ips = load_allowed_ips(self.SETTING_KEY_NAME)
