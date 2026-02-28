from src.harpi_lib.nested import get_nested_attr


class SimpleObject:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestGetNestedAttr:
    def test_simple_attribute(self):
        obj = SimpleObject(name="test")
        result = get_nested_attr(obj, "name", "default")
        assert result == "test"

    def test_nested_attribute(self):
        inner = SimpleObject(value=42)
        outer = SimpleObject(inner=inner)
        result = get_nested_attr(outer, "inner.value", "default")
        assert result == 42

    def test_deep_nesting(self):
        level3 = SimpleObject(data="deep")
        level2 = SimpleObject(level3=level3)
        level1 = SimpleObject(level2=level2)
        result = get_nested_attr(level1, "level2.level3.data", "default")
        assert result == "deep"

    def test_missing_attribute_returns_default(self):
        obj = SimpleObject(name="test")
        result = get_nested_attr(obj, "missing", "default_value")
        assert result == "default_value"

    def test_none_mid_chain_returns_default(self):
        inner = SimpleObject(value=None)
        outer = SimpleObject(inner=inner)
        result = get_nested_attr(outer, "inner.value.something", "default")
        assert result == "default"

    def test_missing_nested_attribute_returns_default(self):
        inner = SimpleObject(value=42)
        outer = SimpleObject(inner=inner)
        result = get_nested_attr(outer, "inner.missing", "default")
        assert result == "default"

    def test_default_can_be_any_type(self):
        obj = SimpleObject()
        assert get_nested_attr(obj, "missing", None) is None
        assert get_nested_attr(obj, "missing", 0) == 0
        assert get_nested_attr(obj, "missing", []) == []
        assert get_nested_attr(obj, "missing", {}) == {}

    def test_with_real_object(self):
        class Parent:
            def __init__(self):
                self.child = Child()

        class Child:
            def __init__(self):
                self.name = "child_name"

        parent = Parent()
        result = get_nested_attr(parent, "child.name", "default")
        assert result == "child_name"

    def test_empty_chain(self):
        obj = SimpleObject(name="test")
        result = get_nested_attr(obj, "", "default")
        assert result == obj or result == "default"
