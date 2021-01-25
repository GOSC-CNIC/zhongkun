"""
The model Network of OCCI – Infrastructure, Reference ooi (https://opendev.org/x/ooi)
"""
from occi import core
from .compute import Compute


class OSTemplate(core.Mixin):
    scheme = core.build_scheme("infrastructure")
    _location = "os_tpl"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("location", self._location + "/")
        kwargs.setdefault("applies", [Compute.kind])
        super(OSTemplate, self).__init__(scheme=self.scheme, *args, **kwargs)


class OCCIResourceTemplate(core.Mixin):
    scheme = core.build_scheme("infrastructure")
    _location = "resource_tpl"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("location", self._location + "/")
        kwargs.setdefault("applies", [Compute.kind])
        super(OCCIResourceTemplate, self).__init__(scheme=self.scheme, *args, **kwargs)


os_tpl = OSTemplate(term="os_tpl", title="OCCI OS Template")
resource_tpl = OCCIResourceTemplate(term="resource_tpl", title="OCCI Resource Template")
