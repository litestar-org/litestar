use std::collections::HashMap;

use pyo3::{
    prelude::*,
    types::{IntoPyDict, PyDict, PyTuple, PyType},
};

use crate::route_map::StarliteContext;

/// Splits a path on '/' and adds all of the 'components' to a new Vec.
/// '/' itself is the first component by default since a leading slash
/// is required by convention
pub fn get_base_components(path: &str) -> Vec<&str> {
    let path_split = path.split('/');

    let mut components = Vec::<&str>::with_capacity(path_split.size_hint().0 + 1);
    components.push("/");

    path_split
        .filter(|component| !component.is_empty())
        .for_each(|component| components.push(component));

    components
}

/// Given two HashMap slices representing lists of path parameter definition objects,
/// returns whether they are equal. This is just implementing PartialEq, for this type,
/// but with a normal function because a Python instance is required
pub fn path_parameters_eq(
    a: &[HashMap<String, Py<PyAny>>],
    b: &[HashMap<String, Py<PyAny>>],
    py: Python,
) -> PyResult<bool> {
    let mut eq = true;
    if a.len() != b.len() {
        eq = false;
    } else {
        for (a, b) in a.iter().zip(b.iter()) {
            if !a.into_py_dict(py).eq(b.into_py_dict(py))? {
                eq = false;
                break;
            }
        }
    }
    Ok(eq)
}

/// Constructs a middleware stack that serves as the point of entry for each route
pub fn build_route_middleware_stack(
    py: Python,
    ctx: &StarliteContext,
    route: &PyAny,
    route_handler: &PyAny,
) -> PyResult<Py<PyAny>> {
    let route_handle = route.getattr("handle")?;
    let exception_handlers = route_handler
        .getattr("resolve_exception_handlers")?
        .call0()?;

    let StarliteContext {
        exception_handler_middleware,
        starlette_middleware,
        debug,
        ..
    } = ctx;

    // we wrap the route.handle method in ExceptionHandlerMiddleware
    let mut asgi_handler = wrap_in_exception_handler(
        py,
        exception_handler_middleware,
        route_handle,
        exception_handlers,
        *debug,
    )?;

    let all_route_handler_middleware: Vec<&PyAny> = route_handler
        .getattr("resolve_middleware")?
        .call0()?
        .extract()?;

    for middleware in all_route_handler_middleware {
        let args = PyDict::new(py);
        args.set_item("app", asgi_handler)?;

        if middleware.is_instance(starlette_middleware.as_ref(py))? {
            let middleware_options = middleware.getattr("options")?.downcast::<PyDict>()?.items();

            for pair in middleware_options.iter() {
                let pair = pair.downcast::<PyTuple>()?;
                let key = pair.get_item(0)?;
                let value = pair.get_item(1)?;
                args.set_item(key, value)?;
            }

            asgi_handler = middleware
                .getattr("cls")?
                .call((), Some(args))?
                .to_object(py);
        } else {
            asgi_handler = middleware.call((), Some(args))?.to_object(py);
        }
    }

    // we wrap the entire stack again in ExceptionHandlerMiddleware
    let exception_handlers = route_handler
        .getattr("resolve_exception_handlers")?
        .call0()?;

    wrap_in_exception_handler(
        py,
        exception_handler_middleware,
        asgi_handler.as_ref(py),
        exception_handlers,
        *debug,
    )
}

/// Wraps the given ASGIApp in an instance of ExceptionHandlerMiddleware
fn wrap_in_exception_handler(
    py: Python,
    exception_handler_middleware: &Py<PyType>,
    app: &PyAny,
    exception_handlers: &PyAny,
    debug: bool,
) -> PyResult<Py<PyAny>> {
    let args = PyDict::new(py);
    args.set_item("app", app)?;
    args.set_item("exception_handlers", exception_handlers)?;
    args.set_item("debug", debug)?;

    exception_handler_middleware.call(py, (), Some(args))
}

/// Gets a particular attribute from a module and converts it into Python type T
pub fn get_attr_and_downcast<T>(module: &PyAny, attr: &str) -> PyResult<Py<T>>
where
    for<'py> T: PyTryFrom<'py>,
    for<'py> &'py T: Into<Py<T>>,
{
    Ok(module.getattr(attr)?.downcast::<T>()?.into())
}
