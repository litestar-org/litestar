from starlite import cached_property


def test_cached_property():
    class TestClass:
        @cached_property
        def my_property(self):
            """Test"""
            return True, object()

        def my_method(self):
            pass

    for c_type in [TestClass, type("Sub", (TestClass,), {})]:
        instance = c_type()
        class_attribute = getattr(TestClass, "my_property")
        assert class_attribute.__doc__ == "Test"
        assert not callable(class_attribute)
        assert isinstance(class_attribute, cached_property)

        # because we also return "object()", the result is not identical between different instances
        assert getattr(instance, "my_property") != getattr(c_type(), "my_property")
        # result is identical because its cached
        assert getattr(instance, "my_property") == getattr(instance, "my_property")
        assert getattr(instance, "my_property")[0] is True
