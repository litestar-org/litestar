use crate::get_attr_and_downcast;
use pyo3::types::{PyDict, PyList, PyMapping};
use pyo3::{
    intern,
    prelude::*,
    types::{PyFunction, PyType},
};

pyo3::import_exception!(starlite.exceptions, ImproperlyConfiguredException);
pyo3::import_exception!(starlite.exceptions, MethodNotAllowedException);
pyo3::import_exception!(starlite.exceptions, NotFoundException);

/// A context object that stores Python handles that are needed in the trie
#[derive(Debug)]
pub(crate) struct StarliteContext {
    /// HTTPRoute
    http_route: Py<PyType>,
    /// WebSocketRoute
    web_socket_route: Py<PyType>,
    /// ASGIRoute
    asgi_route: Py<PyType>,
    /// ExceptionHandlerMiddleware
    exception_handler_middleware: Py<PyType>,
    /// StarletteMiddleware
    starlette_middleware: Py<PyType>,
    /// starlite.parsers.parse_path_params
    parse_path_params: Py<PyFunction>,
    /// starlite instance.debug
    debug: bool,
}

impl StarliteContext {
    pub(crate) fn fetch(py: Python<'_>, debug: bool) -> PyResult<Self> {
        let parsers = py.import("starlite.parsers")?;
        let parse_path_params = get_attr_and_downcast(parsers, "parse_path_params")?;

        let routes = py.import("starlite.routes")?;
        let http_route = get_attr_and_downcast(routes, "HTTPRoute")?;
        let web_socket_route = get_attr_and_downcast(routes, "WebSocketRoute")?;
        let asgi_route = get_attr_and_downcast(routes, "ASGIRoute")?;

        let middleware: &PyAny = py.import("starlite.middleware")?;
        let exception_handler_middleware = middleware
            .getattr("ExceptionHandlerMiddleware")?
            .extract()?;

        let starlette_middleware = py.import("starlette.middleware")?;
        let starlette_middleware = get_attr_and_downcast(starlette_middleware, "Middleware")?;

        Ok(Self {
            http_route,
            web_socket_route,
            asgi_route,
            exception_handler_middleware,
            starlette_middleware,
            parse_path_params,
            debug,
        })
    }

    pub(crate) fn parse_path_parameters<'a>(
        &'a self,
        py: Python<'a>,
        path_parameters: &PyAny,
        raw_params: &[String],
    ) -> PyResult<&'a PyAny> {
        self.parse_path_params
            .as_ref(py)
            .call1((path_parameters, PyList::new(py, raw_params)))
    }

    pub(crate) fn wrap_in_exception_handler<'a>(
        &'a self,
        app: &'a PyAny,
        exception_handlers: &'a PyAny,
        debug: bool,
    ) -> PyResult<&'a PyAny> {
        let py = app.py();
        let args = PyDict::new(py);
        args.set_item("app", app)?;
        args.set_item("exception_handlers", exception_handlers)?;
        args.set_item("debug", debug)?;

        self.exception_handler_middleware
            .as_ref(py)
            .call((), Some(args))
    }

    /// Constructs a middleware stack that serves as the point of entry for each route
    pub(crate) fn build_middleware_stack<'a>(
        &'a self,
        py: Python<'a>,
        route: Route<'_>,
        route_handler: &PyAny,
    ) -> PyResult<Py<PyAny>> {
        let starlette_middleware = self.starlette_middleware.as_ref(py);

        let route_handle = route.handle_fn()?;
        let exception_handlers = route_handler.call_method0("resolve_exception_handlers")?;

        let mut asgi_handler =
            self.wrap_in_exception_handler(route_handle, exception_handlers, self.debug)?;

        let all_route_handler_middleware: Vec<&PyAny> = route_handler
            .call_method0("resolve_middleware")?
            .extract()?;

        for middleware in all_route_handler_middleware {
            let args = PyDict::new(py);
            args.set_item("app", asgi_handler)?;

            if middleware.is_instance(starlette_middleware)? {
                let middleware_options = middleware.getattr("options")?.downcast::<PyDict>()?;
                for (key, value) in middleware_options {
                    args.set_item(key, value)?;
                }

                asgi_handler = middleware.getattr("cls")?.call((), Some(args))?;
            } else {
                asgi_handler = middleware.call((), Some(args))?;
            }
        }

        // we wrap the entire stack again in ExceptionHandlerMiddleware
        let exception_handlers = route_handler.call_method0("resolve_exception_handlers")?;

        Ok(self
            .wrap_in_exception_handler(asgi_handler, exception_handlers, self.debug)?
            .into())
    }
}

#[derive(Debug, Copy, Clone, FromPyObject)]
pub(crate) struct Scope<'a>(&'a PyMapping);

impl<'a> Scope<'a> {
    pub(crate) fn path(&self) -> PyResult<&'a str> {
        self.0.get_item(intern!(self.0.py(), "path"))?.extract()
    }

    pub(crate) fn set_path(&self, new_path: &str) -> PyResult<()> {
        self.0.set_item(intern!(self.0.py(), "path"), new_path)
    }

    pub(crate) fn set_path_params(&self, path_params: &PyAny) -> PyResult<()> {
        self.0
            .set_item(intern!(self.0.py(), "path_params"), path_params)
    }

    pub(crate) fn ty(&self) -> PyResult<&'a str> {
        self.0.get_item(intern!(self.0.py(), "type"))?.extract()
    }

    pub(crate) fn method(&self) -> PyResult<&'a str> {
        self.0.get_item(intern!(self.0.py(), "method"))?.extract()
    }
}

#[derive(Debug, Copy, Clone, FromPyObject)]
pub(crate) struct Route<'a>(&'a PyAny);

impl<'a> Route<'a> {
    pub(crate) fn path(&self) -> PyResult<&'a str> {
        self.0.getattr(intern!(self.0.py(), "path"))?.extract()
    }

    pub(crate) fn path_parameters(&self) -> PyResult<&'a PyAny> {
        self.0.getattr(intern!(self.0.py(), "path_parameters"))
    }

    pub(crate) fn handle_fn(&self) -> PyResult<&'a PyAny> {
        self.0.getattr(intern!(self.0.py(), "handle"))
    }

    pub(crate) fn handler(&self) -> PyResult<&'a PyAny> {
        self.0.getattr(intern!(self.0.py(), "route_handler"))
    }

    pub(crate) fn http_handlers(
        &self,
    ) -> PyResult<impl Iterator<Item = PyResult<(&'a str, &'a PyAny)>>> {
        let mapping: &PyDict = self
            .0
            .getattr(intern!(self.0.py(), "route_handler_map"))?
            .downcast()?;
        let iter = mapping.iter();
        Ok(iter.map(|item| -> PyResult<(&'a str, &'a PyAny)> {
            let name: &str = item.0.extract()?;
            let handler = item.1.get_item(0)?;
            Ok((name, handler))
        }))
    }

    pub(crate) fn is_http(&self, ctx: &StarliteContext) -> PyResult<bool> {
        self.0.is_instance(ctx.http_route.as_ref(self.0.py()))
    }

    pub(crate) fn is_websocket(&self, ctx: &StarliteContext) -> PyResult<bool> {
        self.0.is_instance(ctx.web_socket_route.as_ref(self.0.py()))
    }

    pub(crate) fn is_asgi(&self, ctx: &StarliteContext) -> PyResult<bool> {
        self.0.is_instance(ctx.asgi_route.as_ref(self.0.py()))
    }

    pub(crate) fn type_name(&self) -> PyResult<&'a str> {
        self.0.get_type().name()
    }
}

#[derive(Debug, Copy, Clone, FromPyObject)]
pub(crate) struct PathParameter<'a>(&'a PyAny);

impl<'a> PathParameter<'a> {
    pub(crate) fn full(&self) -> PyResult<&'a str> {
        let full = self.0.get_item(intern!(self.0.py(), "full"))?;
        full.extract()
    }
}

#[derive(Debug, FromPyObject)]
pub(crate) struct ExceptionHandlerMiddleware(Py<PyType>);

impl ExceptionHandlerMiddleware {}
