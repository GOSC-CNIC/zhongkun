"""
The models of OCCI core, Reference ooi (https://opendev.org/x/ooi)
"""
import enum
import copy
import numbers
from urllib.parse import urljoin


SCHEME_PREFIX = "http://schemas.ogf.org/occi"


def build_scheme(category, prefix=SCHEME_PREFIX):
    url = urljoin(prefix, category)
    return f'{url}#'


class AttributeType(enum.Enum):
    NUMBER = 1
    STRING = 2
    BOOLEAN = 3
    LIST = 4
    HASH = 5
    OBJECT = 6

    def check_type(self, value, raise_exception: bool = True):
        """
        :return: bool
            True        # pass
            False       # different data type
        :raises:  TypeError
        """
        if value is None:
            return True

        raise_exc = None
        if self.value == AttributeType.NUMBER.value:
            if isinstance(value, bool) or not isinstance(value, numbers.Number):
                raise_exc = TypeError("Expecting numeric value")
        elif self.value == AttributeType.STRING.value:
            if not isinstance(value, str):
                raise_exc = TypeError("Expecting string type")
        elif self.value == AttributeType.BOOLEAN.value:
            if not isinstance(value, bool):
                raise_exc = TypeError("Expecting boolean value")
        elif self.value == AttributeType.LIST.value:
            if not isinstance(value, list):
                raise_exc = TypeError("Expecting list type")
        elif self.value == AttributeType.HASH.value:
            if not isinstance(value, dict):
                raise_exc = TypeError("Expecting hash type")
        else:       # object
            pass

        if raise_exc is None:
            return True

        if raise_exception:
            raise raise_exc

        return False


class Attribute:
    def __init__(self, name, value=None, mutable=False, required=False, default=None,
                 description=None, attr_type=None):
        self._name = name
        self.required = required
        self.mutable = mutable
        self.default = default
        self.description = description
        if not attr_type:
            self.attr_type = AttributeType.OBJECT
        elif isinstance(attr_type, AttributeType):
            self.attr_type = attr_type
        else:
            raise TypeError("Unexpected attribute type")

        self.attr_type.check_type(value)
        self._value = value

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value

    def __repr__(self):
        return f"{type(self)}('{self.name}', value={self.value}, mutable={self.mutable}, required={self.required})"


class MutableAttribute(Attribute):
    """
    值可变属性
    """
    def __init__(self, *args, **kwargs):
        super(MutableAttribute, self).__init__(*args, **kwargs)
        self.mutable = True

    @Attribute.value.setter
    def value(self, val):
        self.attr_type.check_type(val)
        self._value = val


class ImmutableAttribute(Attribute):
    """
    值不可变属性
    """
    def __init__(self, *args, **kwargs):
        super(ImmutableAttribute, self).__init__(*args, **kwargs)
        self.mutable = False

    @classmethod
    def from_attr(cls, attr, value=None):
        return cls(name=attr.name, value=value, required=attr.required, default=attr.default,
                   description=attr.description, attr_type=attr.attr_type)


class Category:
    def __init__(self, scheme, term, title, attributes: dict = None, location=None):
        self.scheme = scheme
        self.term = term
        self.title = title
        self.location = location

        if attributes is None:
            self.attributes = {}
        elif isinstance(attributes, dict):
            if not all([isinstance(i, Attribute) for i in attributes.values()]):
                raise TypeError('attributes keys must be of class Attribute')

            self.attributes = attributes
        else:
            raise TypeError('attributes must be a dict')

    @property
    def type_id(self):
        return urljoin(self.scheme, f"#{self.term}")


class Action(Category):
    def __init__(self, scheme, term, title, attributes=None):
        super(Action, self).__init__(scheme, term, title, attributes=attributes)


class Kind(Category):
    def __init__(self, scheme, term, title, attributes=None, location=None,
                 parent=None, actions: list = None):
        super(Kind, self).__init__(scheme, term, title, attributes=attributes, location=location)

        if parent and not isinstance(parent, Kind):
            raise TypeError("Kind instance's parent can only be other Kind instances")

        if not actions:
            actions = []
        elif isinstance(actions, list):
            if not all([isinstance(i, Action) for i in actions]):
                raise TypeError('attributes keys must be of class Attribute')
        else:
            raise TypeError('actions must be a list')

        self.parent = parent
        self.actions = actions


class Mixin(Category):
    def __init__(self, scheme, term, title, attributes=None, location=None,
                 depends: list = None, applies: list = None, actions: list = None):
        super(Mixin, self).__init__(scheme, term, title, attributes=attributes, location=location)

        if depends and not all([isinstance(item, Mixin) for item in depends]):
            raise TypeError('depends items must be of class Mixin')

        if actions and not all([isinstance(item, Action) for item in actions]):
            raise TypeError('actions items must be of class Action')

        if applies and not all([isinstance(item, Kind) for item in applies]):
            raise TypeError('actions items must be of class Kind')

        self.depends = depends if applies else []
        self.actions = actions if actions else []
        self.applies = applies if applies else []


class EntityMeta(type):
    def __new__(mcs, name, bases, dct):
        for kls in bases:
            if "attributes" in vars(kls):
                dct["attributes"].update(kls.attributes)

        return super(EntityMeta, mcs).__new__(mcs, name, bases, dct)

    def __init__(cls, *args):
        super(EntityMeta, cls).__init__(*args)


class Entity(metaclass=EntityMeta):
    attributes = {
        "occi.core.id": ImmutableAttribute(
            "occi.core.id", description="A unique identifier",
            attr_type=AttributeType.STRING),
        "occi.core.title": MutableAttribute(
            "occi.core.title", description="The display name of the instance",
            attr_type=AttributeType.STRING),
    }

    kind = Kind(scheme=build_scheme('core'), term='entity', title='entity', location='entity/',
                attributes=attributes)

    actions = None

    def __init__(self, _id, title, mixins: list, kind=None):
        if kind:
            if isinstance(kind, Kind):
                raise TypeError('not a valid Kind instance')

            self.kind = kind

        if mixins and not all([isinstance(i, Mixin) for i in mixins]):
            raise TypeError('mixins items must be of class Mixin')

        self.mixins = mixins if mixins else []
        self.attributes = copy.deepcopy(self.attributes)
        self.attributes["occi.core.id"] = (ImmutableAttribute(
            name="occi.core.id", value=_id, description="A unique identifier", attr_type=AttributeType.STRING))
        self.title = title

    @property
    def id(self):
        return self.attributes["occi.core.id"].value

    @property
    def title(self):
        return self.attributes["occi.core.title"].value

    @title.setter
    def title(self, value):
        self.attributes["occi.core.title"].value = value

    @property
    def location(self):
        return urljoin(self.kind.location, self.id)


class Link(Entity):
    attributes = {
        "occi.core.source": MutableAttribute(
            "occi.core.source", required=True,
            description="The Resource instance the link originates from",
            attr_type=AttributeType.OBJECT),
        "occi.core.target": MutableAttribute(
            "occi.core.target", required=True,
            description=("The unique identifier of an Object this Link "
                         "instance points to"),
            attr_type=AttributeType.OBJECT),
    }

    kind = Kind(scheme=build_scheme('core'), term='link', title='link', location='link/',
                attributes=attributes)

    def __init__(self, _id, title, mixins, source, target, kind=None):
        if not kind:
            kind = self.kind

        super(Link, self).__init__(_id=_id, title=title, kind=kind, mixins=mixins)
        self.source = source
        self.target = target

    @property
    def source(self):
        return self.attributes["occi.core.source"].value

    @source.setter
    def source(self, value):
        self.attributes["occi.core.source"].value = value

    @property
    def target(self):
        return self.attributes["occi.core.target"].value

    @target.setter
    def target(self, value):
        self.attributes["occi.core.target"].value = value


class Resource(Entity):
    attributes = {
        "occi.core.summary": MutableAttribute(
            "occi.core.summary", description=("A summarizing description of "
                                              "the resource instance."),
            attr_type=AttributeType.STRING),
    }

    kind = Kind(scheme=build_scheme('core'), term='resource', title='resource', location='resource/',
                attributes=attributes, parent=Entity.kind)

    def __init__(self, _id, title, mixins, summary=None, kind=None):
        super(Resource, self).__init__(_id=_id, title=title, kind=kind, mixins=mixins)
        self.summary = summary
        self._links = []

    def __eq__(self, other):
        return all([self.attributes[i].value == other.attributes[i].value
                    for i in self.attributes])

    @property
    def links(self):
        return self._links

    def link(self, target, mixins=None):
        li = Link(_id='', title="", mixins=mixins, source=self, target=target)
        self._links.append(li)

    def add_link(self, link):
        self._links.append(link)

    @property
    def summary(self):
        return self.attributes["occi.core.summary"].value

    @summary.setter
    def summary(self, value):
        self.attributes["occi.core.summary"].value = value


class Collection(object):
    def __init__(self, kinds=None, mixins=None, actions=None,
                 resources=None, links=None):
        self.kinds = kinds if kinds else []
        self.mixins = mixins if mixins else []
        self.actions = actions if actions else []
        self.resources = resources if resources else []
        self.links = links if links else []
