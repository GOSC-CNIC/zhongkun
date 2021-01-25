"""
The model Network of OCCI – Infrastructure, Reference ooi (https://opendev.org/x/ooi)
"""
from occi import core


class NetworkActions:
    up = core.Action(scheme=core.build_scheme('infrastructure/compute/action'),
                     term="up", title="start compute instance")
    down = core.Action(scheme=core.build_scheme('infrastructure/compute/action'),
                       term="down", title="start compute instance")
    actions = [up, down]


class NetworkState:
    active = 'active'
    inactive = 'inactive'
    error = 'error'


class Network(core.Resource):
    attributes = {
        "occi.network.vlan": core.MutableAttribute(
            name="occi.network.vlan", description="802.1q VLAN identifier",
            attr_type=core.AttributeType.string_type),
        "occi.network.label": core.MutableAttribute(
            name="occi.network.label", description="Tag based VLANs",
            attr_type=core.AttributeType.string_type),
        "occi.network.state": core.ImmutableAttribute(
            name="occi.network.state", description="Current state of the instance",
            attr_type=core.AttributeType.string_type),
        "occi.network.state.message": core.ImmutableAttribute(
            name="occi.network.state.message",
            description="Human-readable explanation of the current instance state",
            attr_type=core.AttributeType.string_type),
    }

    actions = NetworkActions.actions
    kind = core.Kind(scheme=core.build_scheme('infrastructure'), term='network',
                     title='network resource', attributes=attributes, location='network/',
                     actions=actions, parent=core.Resource.kind)

    def __init__(self, title, summary=None, _id=None, vlan=None, label=None,
                 state=None, message=None, mixins=None):
        super(Network, self).__init__(_id=_id, title=title, mixins=mixins, summary=summary)
        self.vlan = vlan
        self.label = label
        self.attributes["occi.network.state"] = core.ImmutableAttribute.from_attr(
            self.attributes["occi.network.state"], state)
        self.attributes["occi.network.state.message"] = core.ImmutableAttribute(
            self.attributes["occi.network.state.message"], message)

    @property
    def vlan(self):
        return self.attributes["occi.network.vlan"].value

    @vlan.setter
    def vlan(self, value):
        self.attributes["occi.network.vlan"].value = value

    @property
    def label(self):
        return self.attributes["occi.network.label"].value

    @label.setter
    def label(self, value):
        self.attributes["occi.network.label"].value = value

    @property
    def state(self):
        return self.attributes["occi.network.state"].value

    @property
    def message(self):
        return self.attributes["occi.network.state.message"].value


ip_network = core.Mixin(
    scheme=core.build_scheme("infrastructure/network"),
    term="ipnetwork", title="IP Networking Mixin", location="ipnetwork/",
    attributes={
        "occi.network.address": core.MutableAttribute(
            "occi.network.address",
            description="Internet Protocol (IP) network address",
            attr_type=core.AttributeType.string_type),
        "occi.network.gateway": core.MutableAttribute(
            "occi.network.gateway",
            description="Internet Protocol (IP) network address",
            attr_type=core.AttributeType.string_type),
        "occi.network.allocation": core.MutableAttribute(
            "occi.network.allocation",
            description="Address allocation mechanism: dynamic, static",
            attr_type=core.AttributeType.string_type),
    },
    applies=[Network.kind])


class NetworkInterfaceState:
    active = 'active'
    inactive = 'inactive'
    error = 'error'


class NetworkInterface(core.Link):
    attributes = {
        "occi.networkinterface.interface": core.ImmutableAttribute(
            name="occi.networkinterface.interface",
            description="Identifier that relates the link to the link's device interface.",
            attr_type=core.AttributeType.STRING),
        "occi.networkinterface.mac": core.MutableAttribute(
            name="occi.networkinterface.mac",
            description="MAC address associated with the link's device interface.",
            attr_type=core.AttributeType.STRING),
        "occi.networkinterface.state": core.ImmutableAttribute(
            name="occi.networkinterface.state",
            description="Current state of the instance",
            attr_type=core.AttributeType.STRING),
        "occi.networkinterface.state.message": core.ImmutableAttribute(
            name="occi.networkinterface.state.message",
            description="Human-readable explanation of the current instance state",
            attr_type=core.AttributeType.STRING),
    }

    kind = core.Kind(scheme=core.build_scheme('infrastructure'), term='networkinterface',
                     title='network link resource', attributes=attributes, location='networklink/',
                     parent=core.Link.kind)

    def __init__(self, mixins, source, target, _id=None, interface=None,
                 mac=None, state=None, message=None):

        super(NetworkInterface, self).__init__(_id=_id, title=None, mixins=mixins, source=source, target=target)

        self.attributes["occi.networkinterface.interface"] = core.ImmutableAttribute.from_attr(
            self.attributes["occi.networkinterface.interface"], interface)
        self.mac = mac
        self.attributes["occi.networkinterface.state"] = core.ImmutableAttribute.from_attr(
            self.attributes["occi.networkinterface.state"], state)
        self.attributes["occi.networkinterface.state.message"] = core.ImmutableAttribute.from_attr(
            self.attributes["occi.networkinterface.state.message"], message)

    @property
    def interface(self):
        return self.attributes["occi.networkinterface.interface"].value

    @property
    def mac(self):
        return self.attributes["occi.networkinterface.mac"].value

    @mac.setter
    def mac(self, value):
        self.attributes["occi.networkinterface.mac"].value = value

    @property
    def state(self):
        return self.attributes["occi.networkinterface.state"].value

    @property
    def message(self):
        return self.attributes["occi.networkinterface.state.message"].value


ip_network_interface = core.Mixin(
    scheme=core.build_scheme("infrastructure/networkinterface"),
    term="ipnetworkinterface", title="IP Network interface Mixin",
    location="ipnetworkinterface/",
    attributes={
        "occi.networkinterface.address": core.MutableAttribute(
            name="occi.networkinterface.address",
            description="Internet Protocol (IP) network address of the link",
            attr_type=core.AttributeType.STRING),
        "occi.networkinterface.gateway": core.MutableAttribute(
            name="occi.networkinterface.gateway",
            description="Internet Protocol (IP) network address",
            attr_type=core.AttributeType.STRING),
        "occi.networkinterface.allocation": core.MutableAttribute(
            name="occi.networkinterface.allocation",
            description="Address allocation mechanism: dynamic, static",
            attr_type=core.AttributeType.STRING),
    },
    applies=[NetworkInterface.kind])
