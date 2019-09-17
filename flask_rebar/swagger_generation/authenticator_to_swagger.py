from collections import namedtuple

from flask_rebar.utils.deprecation import deprecated, deprecated_parameters
from flask_rebar.authenticators import (
    HeaderApiKeyAuthenticator,
    USE_DEFAULT,
    Authenticator,
)
from .marshmallow_to_swagger import ConverterRegistry
from . import swagger_words as sw


_Context = namedtuple(
    "_Context",
    [
        # The major version of OpenAPI being converter for
        "openapi_version"
    ],
)


class AuthenticatorConverter(object):
    """
    Abstract class for objects that convert Authenticator objects to
    security JSONSchema.
    """

    AUTHENTICATOR_TYPE = None

    def get_security_schemes(self, obj, context):
        """
        Get the security schemes for the provided Authenticator object
        :param flask.authenticators.Authenticator obj:
        :param _Context context:
        :rtype: dict
        """
        raise NotImplementedError()

    def get_security_requirements(self, obj, context):
        """
        Get the security requirements for the provided Authenticator object

        :param flask_rebar.authenticators.Authenticator obj:
        :param _Context context:
        :rtype: list
        """
        raise NotImplementedError()


def make_class_from_method(authenticator_class, func):
    """
    Utility to handle converting old-style method converters into new-style AuthenticatorConverters.
    """
    name = authenticator_class.__name__ + "Converter"
    meta = {
        "AUTHENTICATOR_TYPE": authenticator_class,
        "get_security_schemes": lambda self, obj, context: dict([func(obj)]),
        "get_security_requirements": lambda self, obj, context: [{func(obj)[0]: []}],
    }
    return type(name, (AuthenticatorConverter,), meta)


class HeaderApiKeyConverter(AuthenticatorConverter):

    AUTHENTICATOR_TYPE = HeaderApiKeyAuthenticator

    def get_security_requirements(self, obj, context):
        """
        :param HeaderApiLeyAuthenticator obj:
        :param _Context context:
        :return: list
        """
        return [{obj.name: []}]

    def get_security_schemes(self, obj, context):
        """
        :param HeaderApiLeyAuthenticator obj:
        :param _Context context:
        :return: dict
        """
        return {
            obj.name: {sw.type_: sw.api_key, sw.in_: sw.header, sw.name: obj.header}
        }


class AuthenticatorConverterRegistry(ConverterRegistry):
    def _convert(self, obj, context):
        pass

    def convert(self, obj, openapi_version=2):
        raise RuntimeWarning("Use get_security_schemes or get_security_requirements")

    def register_type(self, converter):
        """
        Registers a converter.

        :param AuthenticatorConverter converter:
        """
        self._type_map[converter.AUTHENTICATOR_TYPE] = converter

    def register_types(self, converters):
        """
        Registers multiple converters.

        :param iterable[AuthenticatorConverter] converters:
        """
        super(AuthenticatorConverterRegistry, self).register_types(converters)

    def get_security_schemes(self, authenticator, openapi_version=2):
        """
        Get the security schemes for the provided Authenticator object
        :param flask.authenticators.Authenticator obj:
        :param int openapi_version: major version of OpenAPI to convert obj for
        :rtype: dict
        """
        # Remove this once legacy is gone
        if not isinstance(authenticator, Authenticator):
            return self.get_security_schemes_legacy(registry=authenticator)
        return self._get_converter_for_type(authenticator).get_security_schemes(
            authenticator, _Context(openapi_version=openapi_version)
        )

    def get_security_requirements(self, authenticator, openapi_version=2):
        """
        Get the security requirements for the provided Authenticator object

        :param flask_rebar.authenticators.Authenticator obj:
        :param int openapi_version: major version of OpenAPI to convert obj for
        :rtype: list
        """
        return self._get_converter_for_type(authenticator).get_security_requirements(
            authenticator, _Context(openapi_version=openapi_version)
        )

    @deprecated_parameters(converters=("", "2.0"))
    def __init__(self, *args, **kwargs):
        super(AuthenticatorConverterRegistry, self).__init__()
        deprecated_converts = args[0] if args else kwargs.get("", {})
        for authenticator, method in deprecated_converts.items():
            self.register(authenticator, method)

    @deprecated("register_type", eol_version="2.0")
    def register(self, authenticator_class, converter):
        converter = make_class_from_method(authenticator_class, converter)
        self.register_type(converter())

    @deprecated("get_security_requirements", eol_version="2.0")
    def get_security_requirement(self, authenticator):
        return self.get_security_requirements(authenticator)

    @deprecated(eol_version="2.0")
    def get_security_schemes_legacy(self, registry):
        """Get the security schemes for the provided `registry`
        :param flask_rebar.rebar.HandlerRegistry registry:
        :rtype: dict
        """
        from flask_rebar.swagger_generation.generator_utils import (
            get_unique_authenticators,
        )

        security_definitions = {}

        authenticators = get_unique_authenticators(registry)

        for authenticator in authenticators:
            security_definitions.update(self.get_security_schemes(authenticator))

        return security_definitions


authenticator_converter_registry = AuthenticatorConverterRegistry()
authenticator_converter_registry.register_types((HeaderApiKeyConverter(),))