import json
import abc
from urllib.parse import urljoin

from occi import core


class JsonRenderer(metaclass=abc.ABCMeta):
    media_type = 'application/json'
    format = 'json'

    def __init__(self, obj):
        self.obj = obj
        self._data = None

    @abc.abstractmethod
    def to_dict(self, request=None):
        raise NotImplementedError(f"The method 'to_dict' of {type(self)} is not implemented")

    @property
    def data(self):
        if not self._data:
            self._data = self.to_dict()
        return self._data

    def render(self):
        return json.dumps(self.data)


class AttributeRenderer(JsonRenderer):
    attr_type_names = {
        core.AttributeType.STRING: "string",
        core.AttributeType.NUMBER: "number",
        core.AttributeType.BOOLEAN: "boolean",
        core.AttributeType.LIST: "array",
        core.AttributeType.HASH: "object",
        core.AttributeType.OBJECT: "string",
    }

    def to_dict(self, request=None):
        if not isinstance(self.obj, core.Attribute):
            raise TypeError('Only render a Attribute instance')

        return {
            'mutable': self.obj.mutable,
            'required': self.obj.required,
            'type': self.attr_type_names[self.obj.attr_type],
            'default': self.obj.default,
            'description': self.obj.description,
            # 'pattern': None
        }


class CategoryRenderer(JsonRenderer):
    def _attributes(self):
        r = {}
        attributes = self.obj.attributes or {}
        for name, attr in attributes.items():
            r[name] = AttributeRenderer(attr).to_dict()

        return r

    def _actions(self):
        actions = []
        if hasattr(self.obj, 'actions') and self.obj.actions:
            for a in self.obj.actions:
                actions.append(a.type_id)

        return {'actions': actions}

    def _location(self, request):
        if getattr(self.obj, "location"):
            location = self.obj.location
            if request:
                location = request.build_absolute_uri(location)

            return {'location': location}

        return {}

    def to_dict(self, request=None):
        if not isinstance(self.obj, core.Category):
            raise TypeError('Only render a Category instance')

        r = {
            'term': self.obj.term,
            'scheme': self.obj.scheme,
            'title': self.obj.title,
            'attributes': self._attributes(),
            'actions': self._actions()
        }

        location = self._location(request)
        r.update(location)
        actions = self._actions()
        r.update(actions)


class ActionRenderer(CategoryRenderer):
    def _location(self, request=None):
        return {}

    def _actions(self):
        return {}


class KindRenderer(CategoryRenderer):
    def to_dict(self, request=None):
        r = super().to_dict(request)
        if self.obj.parent:
            r["parent"] = self.obj.parent.type_id

        return r


class MixinRenderer(CategoryRenderer):
    def depends(self):
        depends = getattr(self.obj, 'depends', [])
        return [i.type_id for i in depends]

    def applies(self):
        applies = getattr(self.obj, 'applies', [])
        return [i.type_id for i in applies]

    def to_dict(self, request=None):
        r = super().to_dict(request)
        r["depends"] = self.depends()
        r["applies"] = self.applies()
        return r


class EntityRenderer(JsonRenderer):
    def _mixins(self):
        mixins = getattr(self.obj, 'mixins', [])
        return [o.type_id for o in mixins]

    def _attributes(self):
        r = {}
        attributes = self.obj.attributes or {}
        for name, attr in attributes.items():
            r[name] = AttributeRenderer(attr).to_dict()

        return r

    def _actions(self):
        actions = []
        if hasattr(self.obj, 'actions') and self.obj.actions:
            for a in self.obj.actions:
                actions.append(a.type_id)

        return {'actions': actions}

    def to_dict(self, request=None):
        r = {
            'id': self.obj.id,
            'kind': self.obj.kind.type_id,
            'title': self.obj.title,
            'mixins': self._mixins(),
            'attributes': self._attributes()
        }
        r.update(self._actions())
        return r


class LinkRenderer(EntityRenderer):
    def _source(self, request):
        url = request.path
        return {
            "kind": self.obj.source.kind.type_id,
            "location": urljoin(url, self.obj.source.location)
        }

    def _target(self, request):
        url = request.path
        return {
            "kind": self.obj.target.kind.type_id,
            "location": urljoin(url, self.obj.target.location)
        }

    def to_dict(self, request=None):
        r = super().to_dict(request)
        r['source'] = self._source(request)
        r['target'] = self._target(request)


class ResourceRenderer(EntityRenderer):
    def _links(self):
        r = []
        links = getattr(self.obj, 'links', [])
        for li in links:
            r.append(LinkRenderer(li).to_dict())

        return r

    def to_dict(self, request=None):
        r = super().to_dict(request)
        r['summary'] = self.obj.summary
        r['links'] = self._links()
        return r


class CollectionRenderer(JsonRenderer):
    def to_dict(self, request=None):
        r = {}
        for what in ["kinds", "mixins", "actions", "resources", "links"]:
            attr = getattr(self.obj, what)
            if attr:
                r[what] = [get_renderer(obj).to_dict(request) for obj in attr]

        return r


def get_renderer(obj):
    if isinstance(obj, core.Attribute):
        return AttributeRenderer(obj)
    elif isinstance(obj, core.Action):
        return ActionRenderer(obj)
    elif isinstance(obj, core.Kind):
        return KindRenderer(obj)
    elif isinstance(obj, core.Mixin):
        return MixinRenderer(obj)
    elif isinstance(obj, core.Link):
        return LinkRenderer(obj)
    elif isinstance(obj, core.Resource):
        return ResourceRenderer(obj)
    elif isinstance(obj, core.Collection):
        return CollectionRenderer(obj)
    else:
        return JsonRenderer(obj)
