"""
Реализация Dependency Injection.

Пример использования::

    pg = RegistryValue[asyncpg.Pool]()  # установка зависимостью на основе класса
    pool = asyncpg.create_pool(dsn=settings.PRODUCTION_DB_URL)  # инициализация зависимости
    pg.set(pool)  # внедрить зависимость
    pool = pg.get()  # теперь можно использовать зависимость

При необходимости внедрить другую зависимость, к примеру для тестирования. В этом случае зависимость перезапишется::

    pg.set(mock_pool)

"""
from typing import Generic, List, Type, TypeVar


__all__ = [
    'ImproperlyConfigured',
    'RegistryValue',
    'RegistryCheckException',
    'Registry',
    'RegistryFrozen',
]

ValueT = TypeVar('ValueT')


DEFAULT_ALIAS = 'default'


class ImproperlyConfigured(Exception):
    pass


class RegistryFrozen(Exception):
    pass


class RegistryCheckException(Exception):
    """
    Исключение возникает в случае если в реестре установленны не все объявленные зависимости.
    """


class RegistryValue(Generic[ValueT]):
    """
    Реестр зависимостей.
    """
    _value: ValueT
    _is_initialized = False

    _instances: List['RegistryValue'] = []

    def __new__(cls: Type['RegistryValue[ValueT]']) -> 'RegistryValue[ValueT]':
        o = super().__new__(cls)
        cls._instances.append(o)
        return o

    @property
    def is_initialized(self) -> bool:
        """
        Проверить, была ли установлена зависимость в реестре.
        """
        return self._is_initialized

    @classmethod
    def check_all_initialized(cls) -> None:
        """
        Проверить, все ли компоненты успешно зарегистрированы.
        """
        if not cls._instances:
            raise RegistryCheckException('no registry objects')

        for o in cls._instances:
            if not o.is_initialized:
                orig_class = o.__orig_class__  # type: ignore[attr-defined]
                raise RegistryCheckException(f'registry object is not initialized: {orig_class}')

    @classmethod
    def destroy_all(cls) -> None:
        """
        Отчистить весь реестр.
        """
        for o in cls._instances:
            o._value = None
            o._is_initialized = False
        cls._instances = []

    def get(self) -> ValueT:
        """
        Получить текущую зависимость из реестра.
        """
        return self._value

    def set(self, value: ValueT) -> None:
        """
        Установить зависимость в реестр.
        """
        self._value = value
        self._is_initialized = True


class Registry(Generic[ValueT]):
    def __init__(self) -> None:
        self._registry: dict[str, RegistryValue[ValueT]] = {}
        self._frozen = False

    def freeze(self) -> None:
        for alias, value in self._registry.items():
            if not value.is_initialized:
                raise ImproperlyConfigured(
                    f'Dependency with alias {alias} is not configured',
                )

        self._frozen = True

    def clear(self) -> None:
        self._registry = {}
        self._frozen = False

    def get_aliases(self) -> List[str]:
        return list(self._registry.keys())

    def __call__(self, alias: str = DEFAULT_ALIAS) -> RegistryValue[ValueT]:
        if alias not in self._registry:
            if self._frozen:
                raise RegistryFrozen(
                    'Dependencies can be added to registry '
                    'only on initialization step',
                )
            self._registry[alias] = RegistryValue[ValueT]()
        return self._registry[alias]
