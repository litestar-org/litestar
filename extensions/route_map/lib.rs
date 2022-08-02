//! A route mapping data structure for use in Starlite

mod search;
#[cfg(test)]
mod test;
mod util;
mod wrappers;

use crate::util::{get_attr_and_downcast, get_base_components};

use std::collections::{HashMap, HashSet};
use std::{fmt, mem};

use crate::search::FindResult;
use pyo3::types::PyList;
use pyo3::{exceptions::PyTypeError, prelude::*};

type ASGIApp = PyAny;

#[pymodule]
fn route_map(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<RouteMap>()?;
    Ok(())
}

#[derive(Debug, Clone)]
enum HandlerGroup {
    Static {
        path: String,
        handler: Py<ASGIApp>,
    },
    Asgi {
        path_parameters: Py<PyAny>,
        handler: Py<ASGIApp>,
    },
    NonAsgi {
        path_parameters: Py<PyAny>,
        asgi_handlers: HashMap<HandlerType, Py<ASGIApp>>,
    },
}

impl HandlerGroup {
    fn websocket(path_parameters: Py<PyAny>, handler: Py<ASGIApp>) -> Self {
        Self::NonAsgi {
            path_parameters,
            asgi_handlers: HashMap::from([(HandlerType::Websocket, handler)]),
        }
    }

    fn path_parameters<'a>(&'a self, py: Python<'a>) -> &'a PyAny {
        match self {
            Self::Static { .. } => PyList::empty(py),
            Self::Asgi {
                path_parameters, ..
            } => path_parameters.as_ref(py),
            Self::NonAsgi {
                path_parameters, ..
            } => path_parameters.as_ref(py),
        }
    }

    fn static_path(&self) -> Option<&str> {
        match self {
            Self::Static { path, .. } => Some(path),
            _ => None,
        }
    }

    fn merge(&mut self, py: Python<'_>, other: Self, path: &str) -> PyResult<&mut Self> {
        match (&mut *self, other) {
            (Self::Static { .. }, Self::Static { .. }) => Ok(self),
            (Self::Static { .. }, _) | (_, Self::Static { .. }) => {
                Err(wrappers::ImproperlyConfiguredException::new_err(format!(
                    "Cannot have configured routes below a static path at {path}"
                )))
            }
            (
                Self::Asgi {
                    path_parameters: lhs_params,
                    handler: lhs_handler,
                },
                Self::Asgi {
                    path_parameters: rhs_params,
                    handler: rhs_handler,
                },
            ) => {
                if !lhs_params.as_ref(py).eq(rhs_params.as_ref(py))? {
                    return Err(wrappers::ImproperlyConfiguredException::new_err(format!(
                        "Should not use routes with conflicting path parameters at {path}"
                    )));
                }
                *lhs_handler = rhs_handler;
                Ok(self)
            }
            (Self::Asgi { .. }, _) | (_, Self::Asgi { .. }) => {
                Err(wrappers::ImproperlyConfiguredException::new_err(format!(
                    "ASGI route conflict at {path}. ASGI route handlers handle all methods."
                )))
            }
            (
                Self::NonAsgi {
                    path_parameters: lhs_params,
                    asgi_handlers: lhs_handlers,
                },
                Self::NonAsgi {
                    path_parameters: rhs_params,
                    asgi_handlers: rhs_handlers,
                },
            ) => {
                if !lhs_params.as_ref(py).eq(rhs_params.as_ref(py))? {
                    return Err(wrappers::ImproperlyConfiguredException::new_err(format!(
                        "Should not use routes with conflicting path parameters at {path}"
                    )));
                }

                for (ty, handler) in rhs_handlers {
                    lhs_handlers.insert(ty, handler);
                }
                Ok(self)
            }
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
enum HandlerType {
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

impl fmt::Display for HandlerType {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let s = match self {
            HandlerType::Websocket => "WEBSOCKET",
            HandlerType::HttpGet => "GET",
            HandlerType::HttpPost => "POST",
            HandlerType::HttpDelete => "DELETE",
            HandlerType::HttpPatch => "PATCH",
            HandlerType::HttpPut => "PUT",
            HandlerType::HttpHead => "HEAD",
            HandlerType::HttpOther(s) => s,
        };
        f.write_str(s)
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
        let path_parameters: &PyAny = route.path_parameters()?;
        let is_static = self.static_paths.contains(path);

        let new_handler_group = if is_static {
            if !route.is_asgi(&self.ctx)? {
                return Err(wrappers::ImproperlyConfiguredException::new_err(format!(
                    "Static route handlers must be asgi handlers at {path}"
                )));
            }
            if path_parameters.is_true()? {
                return Err(wrappers::ImproperlyConfiguredException::new_err(format!(
                    "Static routes may not have path parameters at {path}"
                )));
            }
            HandlerGroup::Static {
                path: String::from(path),
                handler: self
                    .ctx
                    .build_middleware_stack(py, route, route.handler()?)?,
            }
        } else if route.is_http(&self.ctx)? {
            let mut asgi_handlers = HashMap::new();
            for item in route.http_handlers()? {
                let (method, handler) = item?;
                asgi_handlers.insert(
                    HandlerType::from_http_method(method),
                    self.ctx.build_middleware_stack(py, route, handler)?,
                );
            }
            HandlerGroup::NonAsgi {
                path_parameters: path_parameters.into(),
                asgi_handlers,
            }
        } else if route.is_asgi(&self.ctx)? {
            HandlerGroup::Asgi {
                path_parameters: path_parameters.into(),
                handler: self
                    .ctx
                    .build_middleware_stack(py, route, route.handler()?)?,
            }
        } else if route.is_websocket(&self.ctx)? {
            HandlerGroup::websocket(
                path_parameters.into(),
                self.ctx
                    .build_middleware_stack(py, route, route.handler()?)?,
            )
        } else {
            return Err(PyTypeError::new_err(format!(
                "Unknown route type {}",
                route.type_name()?,
            )));
        };

        search::find_insert_handler_group(
            &mut self.root,
            &mut self.plain_routes,
            path,
            path_parameters,
            is_static,
            new_handler_group,
        )?;

        Ok(())
    }

    /// Given a scope, retrieves the correct ASGI App for the route
    fn resolve_asgi_app(&self, py: Python<'_>, scope: wrappers::Scope) -> PyResult<Py<PyAny>> {
        let FindResult {
            handler_group,
            param_values,
            changed_path,
        } = self.find_handler_group(scope.path()?)?;
        if let Some(path) = &changed_path {
            scope.set_path(path)?;
        }

        let parsed_parameters =
            self.ctx
                .parse_path_parameters(py, handler_group.path_parameters(py), &param_values)?;
        scope.set_path_params(parsed_parameters)?;

        let asgi_app = match handler_group {
            HandlerGroup::Static { handler, .. } => handler.clone_ref(py),
            HandlerGroup::Asgi { handler, .. } => handler.clone_ref(py),
            HandlerGroup::NonAsgi { asgi_handlers, .. } => {
                let scope_type = scope.ty()?;
                let make_err: fn() -> PyErr;
                let handler_type = if scope_type == "http" {
                    make_err = || wrappers::MethodNotAllowedException::new_err(());
                    HandlerType::from_http_method(scope.method()?)
                } else {
                    make_err = || wrappers::NotFoundException::new_err(());
                    // TODO: Is it correct to assume any non http scope _must_ be for a websocket?
                    HandlerType::Websocket
                };

                asgi_handlers
                    .get(&handler_type)
                    .ok_or_else(make_err)?
                    .clone_ref(py)
            }
        };
        Ok(asgi_app)
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
