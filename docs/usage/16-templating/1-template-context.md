# Template Context

Both [Jinja2](https://jinja.palletsprojects.com/en/3.0.x/) and [Mako](https://www.makotemplates.org/) support passing a context
object to the template as well as defining callables that will be available inside the template.

## Access the request instance through context

Starlite injects the current [request instance][starlite.connection.request.Request] into the template context under `request` key,
which enables accessing the request and through it the app etc.

For example, lets assume there is some value stored on the `app.state.some_key`, we could thus inject it into a Jinja
template by doing something like this:

```html
<html>
    <body>
        <div>
            <span>My state value: {{request.app.state.some_key}}</span>
        </div>
    </body>
</html>
```

Or using a `Mako:`

```html
<html>
    <body>
        <div>
            <span>My state value: ${request.app.state.some_key}</span>
        </div>
    </body>
</html>
```

## Adding CSRF Inputs

Similar to other frameworks such as Django or Laravel, Starlite offers an easy way to add a hidden `<input>` element to
a html form that contains a CSRF token. To use this functionality, you should first configure
[CSRF protection](../7-middleware/3-builtin-middlewares/3-csrf-middleware.md) for the application. With that in place,
you can now insert the CSRF input field inside an HTML form:

```html
<html>
    <body>
        <div>
            <form action="https://myserverurl.com/some-endpoint" method="post">
                {{csrf_input}}
                <label for="fname">First name:</label><br>
                <input type="text" id="fname" name="fname">
                <label for="lname">Last name:</label><br>
                <input type="text" id="lname" name="lname">
            </form>
        </div>
    </body>
</html>
```

Or using the `Mako` syntax:

```html
<html>
    <body>
        <div>
            <form action="https://myserverurl.com/some-endpoint" method="post">
                ${csrf_input}
                <label for="fname">First name:</label><br>
                <input type="text" id="fname" name="fname">
                <label for="lname">Last name:</label><br>
                <input type="text" id="lname" name="lname">
            </form>
        </div>
    </body>
</html>
```

The input is hidden so users cannot see and interact with it. It will though be sent back to the server when submitted,
and the CSRF middleware will check that the token is valid.

## Passing Template Context

Passing context to the template is very simple - its one of the kwargs expected by the [`Template`][starlite.response.TemplateResponse]
container, so simply pass a string keyed dictionary of values:

```python
from starlite import Template, get


@get(path="/info")
def info() -> Template:
    return Template(name="info.html", context={"numbers": "1234567890"})
```
