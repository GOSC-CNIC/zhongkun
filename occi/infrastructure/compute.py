"""
The model Compute of OCCI – Infrastructure, Reference ooi (https://opendev.org/x/ooi)
"""
from occi import core


class ComputeActions:
    start = core.Action(scheme=core.build_scheme('infrastructure/compute/action'),
                        term="start", title="start compute instance")
    stop = core.Action(scheme=core.build_scheme('infrastructure/compute/action'),
                       term="stop", title="stop compute instance")
    restart = core.Action(scheme=core.build_scheme('infrastructure/compute/action'),
                          term="restart", title="restart compute instance")
    suspend = core.Action(scheme=core.build_scheme('infrastructure/compute/action'),
                          term="suspend", title="suspend compute instance")
    save = core.Action(scheme=core.build_scheme('infrastructure/compute/action'),
                       term="save", title="save compute instance")

    actions = [start, stop, restart, suspend, save]


class ComputeStates:
    active = 'active'
    inactive = 'inactive'
    suspended = 'suspended'


class Compute(core.Resource):
    attributes = {
        "occi.compute.architecture": core.MutableAttribute(
            name="occi.compute.architecture",
            description="CPU architecture of the instance",
            attr_type=core.AttributeType.STRING),
        "occi.compute.cores": core.MutableAttribute(
            name="occi.compute.cores",
            description="Number of virtual CPU cores assigned to the instance",
            attr_type=core.AttributeType.NUMBER),
        "occi.compute.hostname": core.MutableAttribute(
            name="occi.compute.hostname",
            description="Fully Qualified DNS hostname for the instance",
            attr_type=core.AttributeType.STRING),
        "occi.compute.share": core.MutableAttribute(
            name="occi.compute.share",
            description="Relative number of CPU shares for the instance",
            attr_type=core.AttributeType.NUMBER),
        "occi.compute.memory": core.MutableAttribute(
            name="occi.compute.memory",
            description="Maximum RAM in gigabytes allocated to the instance",
            attr_type=core.AttributeType.NUMBER),
        "occi.compute.state": core.ImmutableAttribute(
            name="occi.compute.state", description="Current state of the instance",
            attr_type=core.AttributeType.STRING),
        "occi.compute.state.message": core.ImmutableAttribute(
            name="occi.compute.state.message",
            description="Human-readable explanation of the current instance state",
            attr_type=core.AttributeType.STRING),
    }
    actions = ComputeActions.actions
    kind = core.Kind(scheme=core.build_scheme('infrastructure'), term='compute', title='compute resource',
                     attributes=attributes, location='compute/', actions=actions,
                     parent=core.Resource.kind)

    def __init__(self, title, summary=None, _id=None, architecture=None,
                 cores=None, hostname=None, share=None, memory=None,
                 state=None, message=None, mixins=None):
        super(Compute, self).__init__(_id=_id, title=title, mixins=mixins, summary=summary)
        self.architecture = architecture
        self.cores = cores
        self.hostname = hostname
        self.share = share
        self.memory = memory
        self.attributes["occi.compute.state"] = core.ImmutableAttribute.from_attr(
            self.attributes["occi.compute.state"], state)
        self.attributes["occi.compute.state.message"] = core.ImmutableAttribute.from_attr(
            self.attributes["occi.compute.state.message"], message)

    @property
    def architecture(self):
        return self.attributes["occi.compute.architecture"].value

    @architecture.setter
    def architecture(self, value):
        self.attributes["occi.compute.architecture"].value = value

    @property
    def cores(self):
        return self.attributes["occi.compute.cores"].value

    @cores.setter
    def cores(self, value):
        self.attributes["occi.compute.cores"].value = value

    @property
    def hostname(self):
        return self.attributes["occi.compute.hostname"].value

    @hostname.setter
    def hostname(self, value):
        self.attributes["occi.compute.hostname"].value = value

    @property
    def share(self):
        return self.attributes["occi.compute.share"].value

    @share.setter
    def share(self, value):
        self.attributes["occi.compute.share"].value = value

    @property
    def memory(self):
        return self.attributes["occi.compute.memory"].value

    @memory.setter
    def memory(self, value):
        self.attributes["occi.compute.memory"].value = value

    @property
    def state(self):
        return self.attributes["occi.compute.state"].value

    @property
    def message(self):
        return self.attributes["occi.compute.state.message"].value
