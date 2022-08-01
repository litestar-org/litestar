//! A route mapping data structure for use in Starlite

mod search;
#[cfg(test)]
mod test;
mod util;
mod wrappers;

use crate::util::{get_attr_and_downcast, get_base_components};

use std::collections::{HashMap, HashSet};
use std::mem;

use crate::search::FindResult;
use pyo3::{exceptions::PyTypeError, prelude::*};

type ASGIApp = PyAny;

#[pymodule]
fn route_map(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<RouteMap>()?;
    Ok(())
}

#[derive(Debug, Clone)]
struct HandlerGroup {
    is_asgi: bool,
    static_path: Option<String>,
    path_parameters: Py<PyAny>,
    asgi_handlers: HashMap<HandlerType, Py<ASGIApp>>,
}

impl HandlerGroup {
    fn new(params: Py<PyAny>) -> Self {
        Self {
            path_parameters: params,
            asgi_handlers: Default::default(),
            is_asgi: false,
            static_path: None,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
enum HandlerType {
    Asgi,
    Websocket,
    // HTTP methods taken from starlite.types.Method
    HttpGet,
    HttpPost,
    HttpDelete,
    HttpPatch,
    HttpPut,
    HttpHead,
    HttpOther(String),
}

impl HandlerType {
    fn from_http_method(method: &str) -> Self {
        match method {
            "GET" => Self::HttpGet,
            "POST" => Self::HttpPost,
            "DELETE" => Self::HttpDelete,
            "PATCH" => Self::HttpPatch,
            "PUT" => Self::HttpPut,
            "HEAD" => Self::HttpHead,
            _ => Self::HttpOther(String::from(method)),
        }
    }
}

/// A node for the trie
#[derive(Debug, Clone, Default)]
struct Node {
    // Map from path component to node
    children: HashMap<String, Node>,
    // Child for a placeholder
    placeholder_child: Option<Box<Node>>,
    handler_group: Option<HandlerGroup>,
}

/// A path router based on a prefix tree / trie.
///
/// Stores a handler references and other metadata for each node,
/// as well as both static paths and plain routes for use with Starlite.
///
/// Routes can be added using `add_routes`.
/// Given a scope containing a path, can retrieve handlers using `parse_scope_to_route`.
#[pyclass]
#[derive(Debug)]
pub(crate) struct RouteMap {
    ctx: wrappers::StarliteContext,
    static_paths: HashSet<String>,
    plain_routes: HashMap<String, HandlerGroup>,
    root: Node,
}

// The functions below are available to Python code
#[pymethods]
impl RouteMap {
    /// Creates an empty `RouteMap`
    #[new]
    #[args(debug = false)]
    fn new(py: Python, debug: bool) -> PyResult<Self> {
        Ok(RouteMap {
            ctx: wrappers::StarliteContext::fetch(py, debug)?,
            static_paths: HashSet::new(),
            plain_routes: HashMap::new(),
            root: Node::default(),
        })
    }

    /// Adds a new static path by path name
    fn add_static_path(&mut self, path: &str) {
        self.static_paths.insert(path.to_string());
    }

    /// Checks if a given path refers to a static path
    fn is_static_path(&self, path: &str) -> bool {
        self.static_paths.contains(path)
    }

    /// Removes a path from the static path set
    fn remove_static_path(&mut self, path: &str) -> bool {
        self.static_paths.remove(path)
    }

    /// Add a collection of routes to the map
    #[pyo3(text_signature = "($self, routes)")]
    fn add_routes<'a>(&mut self, py: Python<'a>, routes: Vec<wrappers::Route>) -> PyResult<()> {
        for route in routes {
            self.add_route(py, route)?;
        }
        Ok(())
    }

    /// Add a route to the map
    #[pyo3(text_signature = "($self, route)")]
    fn add_route<'a>(&mut self, py: Python<'a>, route: wrappers::Route<'a>) -> PyResult<()> {
        let path = route.path()?;
        let path_parameters = route.path_parameters()?;
        let is_static = self.static_paths.contains(path);

        let handler_group = search::find_insert_handler_group(
            &mut self.root,
            &mut self.plain_routes,
            path,
            path_parameters,
            is_static,
        )?;

        if path_parameters.ne(&handler_group.path_parameters)? {
            return Err(wrappers::ImproperlyConfiguredException::new_err(
                "Routes with conflicting path parameters",
            ));
        }
        if is_static {
            handler_group.is_asgi = true;
            handler_group.static_path = Some(String::from(path));
        }

        if route.is_http(&self.ctx)? {
            for item in route.http_handlers()? {
                let (method, handler) = item?;
                // TODO: Check for existing?
                handler_group.asgi_handlers.insert(
                    HandlerType::from_http_method(method),
                    self.ctx.build_middleware_stack(py, route, handler)?,
                );
            }
        } else if route.is_asgi(&self.ctx)? {
            handler_group.is_asgi = true;
            handler_group.asgi_handlers.insert(
                HandlerType::Asgi,
                self.ctx
                    .build_middleware_stack(py, route, route.handler()?)?,
            );
        } else if route.is_websocket(&self.ctx)? {
            handler_group.asgi_handlers.insert(
                HandlerType::Websocket,
                self.ctx
                    .build_middleware_stack(py, route, route.handler()?)?,
            );
        } else {
            return Err(PyTypeError::new_err(format!(
                "Unknown route type {}",
                route.type_name()?,
            )));
        }
        Ok(())
    }

    /// Given a scope, retrieves the correct ASGI App for the route
    fn resolve_asgi_app(&self, py: Python<'_>, scope: wrappers::Scope) -> PyResult<Py<PyAny>> {
        let FindResult {
            handler_group,
            param_values,
            changed_path,
        } = self.find_handler_group(scope.path()?)?;
        let HandlerGroup {
            is_asgi,
            path_parameters,
            asgi_handlers,
            ..
        } = handler_group;

        if let Some(path) = &changed_path {
            scope.set_path(path)?;
        }

        let parsed_parameters =
            self.ctx
                .parse_path_parameters(py, path_parameters.as_ref(py), &param_values)?;
        scope.set_path_params(parsed_parameters)?;

        let mut make_err: fn() -> PyErr = || wrappers::NotFoundException::new_err(());
        let handler_type = if *is_asgi {
            HandlerType::Asgi
        } else {
            let scope_type = scope.ty()?;
            if scope_type == "http" {
                make_err = || wrappers::MethodNotAllowedException::new_err(());
                HandlerType::from_http_method(scope.method()?)
            } else {
                // TODO: Is it correct to assume any non http scope _must_ be for a websocket?
                HandlerType::Websocket
            }
        };
        asgi_handlers
            .get(&handler_type)
            .map(|handler: &Py<_>| handler.clone_ref(py))
            .ok_or_else(make_err)
    }

    fn __repr__(&self) -> String {
        format!("{:#?}", self)
    }
}

impl Drop for RouteMap {
    fn drop(&mut self) {
        // Avoid recursively dropping nodes, possibly leading to stack overflow, instead, steal their children
        let mut stack = vec![mem::take(&mut self.root)];
        while let Some(mut node) = stack.pop() {
            if let Some(child) = node.placeholder_child.take() {
                stack.push(*child);
            }
            stack.extend(node.children.drain().map(|(_, node)| node));
        }
    }
}
