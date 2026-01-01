"""Tests for LazyOrmProxy."""

from unittest.mock import AsyncMock, MagicMock, patch

from pytest import mark, raises

from asynctasq.serializers.hooks.orm.lazy_proxy import (
    LazyOrmProxy,
    is_lazy_proxy,
    resolve_lazy_proxies,
)


class TestLazyOrmProxy:
    """Tests for LazyOrmProxy class."""

    @mark.asyncio
    async def test_lazy_proxy_initialization(self) -> None:
        """Test LazyOrmProxy initialization."""
        model_class = MagicMock()
        pk = 42
        callback = AsyncMock()

        proxy = LazyOrmProxy(model_class, pk, callback)

        assert proxy._model_class == model_class
        assert proxy._pk == pk
        assert proxy._fetch_callback == callback
        assert proxy._resolved is None

    @mark.asyncio
    async def test_lazy_proxy_resolution(self) -> None:
        """Test LazyOrmProxy resolves correctly."""
        model_class = MagicMock()
        model_class.__name__ = "Product"
        mock_instance = MagicMock()
        callback = AsyncMock(return_value=mock_instance)

        proxy = LazyOrmProxy(model_class, 42, callback)

        # Resolve the proxy
        resolved = await proxy.await_resolve()

        assert resolved == mock_instance
        callback.assert_called_once_with(model_class, 42)

    @mark.asyncio
    async def test_lazy_proxy_caches_resolved_value(self) -> None:
        """Test LazyOrmProxy caches the resolved instance."""
        model_class = MagicMock()
        mock_instance = MagicMock()
        callback = AsyncMock(return_value=mock_instance)

        proxy = LazyOrmProxy(model_class, 42, callback)

        # Resolve twice
        resolved1 = await proxy.await_resolve()
        resolved2 = await proxy.await_resolve()

        # Should call callback only once
        assert resolved1 == resolved2
        callback.assert_called_once()

    @mark.asyncio
    async def test_lazy_proxy_attribute_access_before_resolution(self) -> None:
        """Test accessing attributes before resolution raises error."""
        model_class = MagicMock()
        model_class.__name__ = "Product"
        callback = AsyncMock()

        proxy = LazyOrmProxy(model_class, 42, callback)

        # Try to access attribute before resolution
        with raises(RuntimeError, match="has not been resolved yet"):
            _ = proxy.name  # type: ignore[attr-defined]

    @mark.asyncio
    async def test_lazy_proxy_attribute_access_after_resolution(self) -> None:
        """Test accessing attributes after resolution works."""
        model_class = MagicMock()
        mock_instance = MagicMock()
        mock_instance.name = "Widget"
        callback = AsyncMock(return_value=mock_instance)

        proxy = LazyOrmProxy(model_class, 42, callback)

        # Resolve first
        await proxy.await_resolve()

        # Now attribute access should work
        assert proxy.name == "Widget"  # type: ignore[attr-defined]

    @mark.asyncio
    async def test_lazy_proxy_setattr_after_resolution(self) -> None:
        """Test setting attributes after resolution works."""
        model_class = MagicMock()
        mock_instance = MagicMock()
        callback = AsyncMock(return_value=mock_instance)

        proxy = LazyOrmProxy(model_class, 42, callback)

        # Resolve first
        await proxy.await_resolve()

        # Set attribute
        proxy.name = "Updated"  # type: ignore[attr-defined]
        assert mock_instance.name == "Updated"

    @mark.asyncio
    async def test_lazy_proxy_setattr_before_resolution(self) -> None:
        """Test setting attributes before resolution raises error."""
        model_class = MagicMock()
        model_class.__name__ = "Product"
        callback = AsyncMock()

        proxy = LazyOrmProxy(model_class, 42, callback)

        # Try to set attribute before resolution
        with raises(RuntimeError, match="Cannot set attribute on unresolved LazyOrmProxy"):
            proxy.name = "Updated"  # type: ignore[attr-defined]

    @mark.asyncio
    async def test_lazy_proxy_awaitable(self) -> None:
        """Test LazyOrmProxy can be awaited directly."""
        model_class = MagicMock()
        mock_instance = MagicMock()
        callback = AsyncMock(return_value=mock_instance)

        proxy = LazyOrmProxy(model_class, 42, callback)

        # Await the proxy directly
        resolved = await proxy
        assert resolved == mock_instance
        callback.assert_called_once_with(model_class, 42)

    @mark.asyncio
    async def test_lazy_proxy_awaitable_caches(self) -> None:
        """Test awaiting proxy multiple times uses cached value."""
        model_class = MagicMock()
        mock_instance = MagicMock()
        callback = AsyncMock(return_value=mock_instance)

        proxy = LazyOrmProxy(model_class, 42, callback)

        # Await twice
        resolved1 = await proxy
        resolved2 = await proxy

        assert resolved1 == resolved2
        callback.assert_called_once()

    @mark.asyncio
    async def test_lazy_proxy_special_attributes_accessible(self) -> None:
        """Test special attributes are accessible without resolution."""
        model_class = MagicMock()
        model_class.__name__ = "Product"
        callback = AsyncMock()

        proxy = LazyOrmProxy(model_class, 42, callback)

        # These should work without resolution
        assert proxy._model_class == model_class
        assert proxy._pk == 42
        assert proxy._fetch_callback == callback
        assert proxy._resolved is None

    def test_lazy_proxy_repr(self) -> None:
        """Test LazyOrmProxy repr."""
        model_class = MagicMock()
        model_class.__name__ = "Product"
        callback = AsyncMock()

        proxy = LazyOrmProxy(model_class, 42, callback)

        repr_str = repr(proxy)
        assert "LazyOrmProxy" in repr_str
        assert "Product" in repr_str
        assert "pk=42" in repr_str
        assert "unresolved" in repr_str

    @mark.asyncio
    async def test_lazy_proxy_repr_resolved(self) -> None:
        """Test LazyOrmProxy repr after resolution."""
        model_class = MagicMock()
        model_class.__name__ = "Product"
        mock_instance = MagicMock()
        callback = AsyncMock(return_value=mock_instance)

        proxy = LazyOrmProxy(model_class, 42, callback)
        await proxy.await_resolve()

        repr_str = repr(proxy)
        assert "LazyOrmProxy" in repr_str
        assert "Product" in repr_str
        assert "pk=42" in repr_str
        assert "resolved" in repr_str

    def test_is_lazy_proxy(self) -> None:
        """Test is_lazy_proxy helper."""
        model_class = MagicMock()
        callback = AsyncMock()

        proxy = LazyOrmProxy(model_class, 42, callback)
        not_proxy = MagicMock()

        assert is_lazy_proxy(proxy) is True
        assert is_lazy_proxy(not_proxy) is False


class TestResolveLazyProxies:
    """Tests for resolve_lazy_proxies utility."""

    @mark.asyncio
    async def test_resolve_single_proxy(self) -> None:
        """Test resolving a single proxy."""
        model_class = MagicMock()
        mock_instance = MagicMock()
        callback = AsyncMock(return_value=mock_instance)

        proxy = LazyOrmProxy(model_class, 42, callback)

        resolved = await resolve_lazy_proxies(proxy)

        assert resolved == mock_instance
        callback.assert_called_once()

    @mark.asyncio
    async def test_resolve_proxies_in_dict(self) -> None:
        """Test resolving proxies in a dictionary."""
        model_class = MagicMock()
        mock_instance = MagicMock()
        callback = AsyncMock(return_value=mock_instance)

        data = {
            "product": LazyOrmProxy(model_class, 42, callback),
            "price": 24.99,
            "name": "Widget",
        }

        resolved = await resolve_lazy_proxies(data)

        assert resolved["product"] == mock_instance
        assert resolved["price"] == 24.99
        assert resolved["name"] == "Widget"

    @mark.asyncio
    async def test_resolve_proxies_in_list(self) -> None:
        """Test resolving proxies in a list."""
        model_class = MagicMock()
        mock1 = MagicMock()
        mock2 = MagicMock()
        callback1 = AsyncMock(return_value=mock1)
        callback2 = AsyncMock(return_value=mock2)

        data = [
            LazyOrmProxy(model_class, 1, callback1),
            "string",
            LazyOrmProxy(model_class, 2, callback2),
        ]

        resolved = await resolve_lazy_proxies(data)

        assert resolved[0] == mock1
        assert resolved[1] == "string"
        assert resolved[2] == mock2

    @mark.asyncio
    async def test_resolve_proxies_in_tuple(self) -> None:
        """Test resolving proxies in a tuple."""
        model_class = MagicMock()
        mock_instance = MagicMock()
        callback = AsyncMock(return_value=mock_instance)

        data = (LazyOrmProxy(model_class, 42, callback), "string", 123)

        resolved = await resolve_lazy_proxies(data)

        assert isinstance(resolved, tuple)
        assert resolved[0] == mock_instance
        assert resolved[1] == "string"
        assert resolved[2] == 123

    @mark.asyncio
    async def test_resolve_nested_structures(self) -> None:
        """Test resolving proxies in nested data structures."""
        model_class = MagicMock()
        mock_instance = MagicMock()
        callback = AsyncMock(return_value=mock_instance)

        data = {
            "products": [
                {"item": LazyOrmProxy(model_class, 1, callback), "qty": 5},
                {"item": LazyOrmProxy(model_class, 2, callback), "qty": 3},
            ],
            "total": 100,
        }

        resolved = await resolve_lazy_proxies(data)

        assert resolved["products"][0]["item"] == mock_instance
        assert resolved["products"][1]["item"] == mock_instance
        assert resolved["total"] == 100

    @mark.asyncio
    async def test_resolve_non_proxy_objects(self) -> None:
        """Test that non-proxy objects are returned unchanged."""
        data = {"string": "test", "number": 42, "list": [1, 2, 3]}

        resolved = await resolve_lazy_proxies(data)

        assert resolved == data

    @mark.asyncio
    async def test_resolve_empty_structures(self) -> None:
        """Test resolving empty data structures."""
        assert await resolve_lazy_proxies({}) == {}
        assert await resolve_lazy_proxies([]) == []
        assert await resolve_lazy_proxies(()) == ()


class TestLazyOrmProxyConfig:
    """Tests for LazyOrmProxy Tortoise config integration."""

    @mark.asyncio
    async def test_resolve_with_config_available(self) -> None:
        """Test proxy resolution when Config has Tortoise settings."""
        from asynctasq.serializers.hooks.orm.lazy_proxy import LazyOrmProxy

        model_class = MagicMock()
        model_class.__name__ = "Product"
        mock_instance = MagicMock()
        callback = AsyncMock(return_value=mock_instance)

        proxy = LazyOrmProxy(model_class, 42, callback)

        # Mock Config.get() to return config with Tortoise settings
        mock_config = MagicMock()
        mock_config.tortoise_orm = {"db_url": "sqlite://:memory:"}

        with (
            patch("asynctasq.config.Config.get", return_value=mock_config),
            patch(
                "asynctasq.serializers.hooks.orm.lazy_proxy.Tortoise", create=True
            ) as mock_tortoise,
        ):
            mock_tortoise._inited = False

            resolved = await proxy._resolve()

            assert resolved == mock_instance
            callback.assert_called_once_with(model_class, 42)

    @mark.asyncio
    async def test_resolve_with_config_error(self) -> None:
        """Test proxy resolution handles Config access errors."""
        from asynctasq.serializers.hooks.orm.lazy_proxy import LazyOrmProxy

        model_class = MagicMock()
        model_class.__name__ = "Product"
        mock_instance = MagicMock()
        callback = AsyncMock(return_value=mock_instance)

        proxy = LazyOrmProxy(model_class, 42, callback)

        # Mock Config.get() to raise exception
        with patch(
            "asynctasq.config.Config.get",
            side_effect=RuntimeError("Config error"),
        ):
            # Should still resolve using callback
            resolved = await proxy._resolve()
            assert resolved == mock_instance

    @mark.asyncio
    async def test_resolve_with_no_config_tortoise_orm(self) -> None:
        """Test proxy resolution when Config exists but no Tortoise settings."""
        from asynctasq.serializers.hooks.orm.lazy_proxy import LazyOrmProxy

        model_class = MagicMock()
        model_class.__name__ = "Product"
        mock_instance = MagicMock()
        callback = AsyncMock(return_value=mock_instance)

        proxy = LazyOrmProxy(model_class, 42, callback)

        # Mock Config with no tortoise_orm
        mock_config = MagicMock()
        mock_config.tortoise_orm = None

        with patch("asynctasq.config.Config.get", return_value=mock_config):
            resolved = await proxy._resolve()
            assert resolved == mock_instance

    @mark.asyncio
    async def test_resolve_with_tortoise_init_error(self) -> None:
        """Test proxy resolution handles Tortoise initialization errors."""
        from asynctasq.serializers.hooks.orm.lazy_proxy import LazyOrmProxy

        model_class = MagicMock()
        model_class.__name__ = "Product"
        mock_instance = MagicMock()
        callback = AsyncMock(return_value=mock_instance)

        proxy = LazyOrmProxy(model_class, 42, callback)

        # Mock Config and Tortoise with error
        mock_config = MagicMock()
        mock_config.tortoise_orm = {"db_url": "sqlite://:memory:"}

        with (
            patch("asynctasq.config.Config.get", return_value=mock_config),
            patch(
                "asynctasq.serializers.hooks.orm.lazy_proxy.Tortoise", create=True
            ) as mock_tortoise,
        ):
            mock_tortoise._inited = False
            # Make await Tortoise.init() raise error
            mock_tortoise.init = AsyncMock(side_effect=RuntimeError("Init failed"))

            # Should still resolve (error is logged but not raised)
            resolved = await proxy._resolve()
            assert resolved == mock_instance

    @mark.asyncio
    async def test_resolve_tortoise_import_error(self) -> None:
        """Test proxy resolution handles Tortoise not being installed."""
        import builtins

        from asynctasq.serializers.hooks.orm.lazy_proxy import LazyOrmProxy

        model_class = MagicMock()
        model_class.__name__ = "Product"
        mock_instance = MagicMock()
        callback = AsyncMock(return_value=mock_instance)

        proxy = LazyOrmProxy(model_class, 42, callback)

        mock_config = MagicMock()
        mock_config.tortoise_orm = {"db_url": "sqlite://:memory:"}

        # Mock the import inside _resolve to raise ImportError for tortoise
        original_import = builtins.__import__

        def selective_import(name, *args, **kwargs):  # type: ignore[no-untyped-def]
            if name == "tortoise":
                raise ImportError("No module named 'tortoise'")
            return original_import(name, *args, **kwargs)

        with (
            patch("asynctasq.config.Config.get", return_value=mock_config),
            patch("builtins.__import__", side_effect=selective_import),
        ):
            # Should resolve without Tortoise
            resolved = await proxy._resolve()
            assert resolved == mock_instance
