# Header and Cookie Parameters

Unlike _Query_ parameters, _Header_ and _Cookie_ parameters have to be declared using
[the Parameter function](3-the-parameter-function.md), for example:

```python
--8<-- "examples/parameters/header_and_cookie_parameters.py"
```


As you can see in the above, header parameters are declared using the `header` kwargs and cookie parameters using
the `cookie` kwarg. Aside form this difference they work the same as query parameters.
