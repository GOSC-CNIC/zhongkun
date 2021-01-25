"""
The model Storage of OCCI – Infrastructure, Reference ooi (https://opendev.org/x/ooi)
"""
from occi import core


class StorageActions:
    ONLINE = core.Action(scheme=core.build_scheme('infrastructure/storage/action'),
                         term="online", title="online storage instance")
    OFFLINE = core.Action(scheme=core.build_scheme('infrastructure/storage/action'),
                          term="offline", title="offline storage instance")
    BACKUP = core.Action(scheme=core.build_scheme('infrastructure/storage/action'),
                         term="backup", title="backup storage instance")
    SNAPSHOT = core.Action(scheme=core.build_scheme('infrastructure/storage/action'),
                           term="snapshot", title="snapshot storage instance")
    RESIZE = core.Action(scheme=core.build_scheme('infrastructure/storage/action'),
                         term="resize", title="resize storage instance")

    actions = [ONLINE, OFFLINE, BACKUP, SNAPSHOT, RESIZE]


class StorageState:
    online = 'online'
    offline = 'offline'
    error = 'error'


class Storage(core.Resource):
    attributes = {
        "occi.storage.size": core.MutableAttribute(
            name="occi.storage.size", required=True,
            description="Storage size of the instance in gigabytes",
            attr_type=core.AttributeType.NUMBER),
        "occi.storage.state": core.ImmutableAttribute(
            name="occi.storage.state", description="Current state of the instance",
            attr_type=core.AttributeType.STRING),
        "occi.storage.state.message": core.ImmutableAttribute(
            name="occi.storage.state.message",
            description="Human-readable explanation of the current instance state",
            attr_type=core.AttributeType.STRING),
    }
    actions = StorageActions.actions
    kind = core.Kind(scheme=core.build_scheme('infrastructure'), term='storage',
                     title='storage resource', attributes=attributes, location='storage/',
                     actions=actions, parent=core.Resource.kind)

    def __init__(self, title='Storage Resource', summary=None, _id=None, size=None, state=None, message=None):
        mixins = []
        super(Storage, self).__init__(_id=_id, title=title, mixins=mixins, summary=summary)
        self.size = size
        self.attributes["occi.storage.state"] = core.ImmutableAttribute.from_attr(
            self.attributes["occi.storage.state"], state)
        self.attributes["occi.storage.state.message"] = core.ImmutableAttribute.from_attr(
            self.attributes["occi.storage.state.message"], message)

    @property
    def size(self):
        return self.attributes["occi.storage.size"].value

    @size.setter
    def size(self, value):
        self.attributes["occi.storage.size"].value = value

    @property
    def state(self):
        return self.attributes["occi.storage.state"].value

    @property
    def message(self):
        return self.attributes["occi.storage.state.message"].value


class StorageLinkState:
    active = 'active'
    inactive = 'inactive'
    error = 'error'


class StorageLink(core.Link):
    attributes = {
        "occi.storagelink.deviceid": core.MutableAttribute(
            name="occi.storagelink.deviceid",
            description="Device identifier as defined by the OCCI service provider",
            attr_type=core.AttributeType.STRING),
        "occi.storagelink.mountpoint": core.MutableAttribute(
            name="occi.storagelink.mountpoint",
            description="Point to where the storage is mounted in the guest OS",
            attr_type=core.AttributeType.STRING),
        "occi.storagelink.state": core.ImmutableAttribute(
            name="occi.storagelink.state",
            description="Current state of the instance",
            attr_type=core.AttributeType.STRING),
        "occi.storagelink.state.message": core.ImmutableAttribute(
            name="occi.storagelink.state.message",
            description="Human-readable explanation of the current instance state",
            attr_type=core.AttributeType.string_type),
    }
    kind = core.Kind(scheme=core.build_scheme('infrastructure'), term='storagelink',
                     title='storage link resource', attributes=attributes, location='storagelink/',
                     parent=core.Link.kind)

    def __init__(self, source, target, device_id=None, mount_point=None,
                 state=None, message=None):

        link_id = '_'.join([source.id, target.id])
        super(StorageLink, self).__init__(None, [], source, target, link_id)

        self.deviceid = device_id
        self.mountpoint = mount_point
        self.attributes["occi.storagelink.state"] = core.ImmutableAttribute.from_attr(
            self.attributes["occi.storagelink.state"], state)
        self.attributes["occi.storagelink.state.message"] = core.ImmutableAttribute.from_attr(
            self.attributes["occi.storagelink.state.message"], message)

    @property
    def deviceid(self):
        return self.attributes["occi.storagelink.deviceid"].value

    @deviceid.setter
    def deviceid(self, value):
        self.attributes["occi.storagelink.deviceid"].value = value

    @property
    def mountpoint(self):
        return self.attributes["occi.storagelink.mountpoint"].value

    @mountpoint.setter
    def mountpoint(self, value):
        self.attributes["occi.storagelink.mountpoint"].value = value

    @property
    def state(self):
        return self.attributes["occi.storagelink.state"].value

    @property
    def message(self):
        return self.attributes["occi.storagelink.state.message"].value
