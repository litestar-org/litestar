//! A route mapping data structure for use in Starlite

#[cfg(test)]
mod test;
mod util;

use crate::util::{
    build_route_middleware_stack, get_attr_and_downcast, get_base_components, path_parameters_eq,
};

use std::collections::{HashMap, HashSet};

use pyo3::{
    prelude::*,
    types::{PyDict, PyFunction, PyTuple, PyType},
};

#[pymodule]
fn route_map(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<RouteMap>()?;
    Ok(())
}

pyo3::import_exception!(starlite.exceptions, ImproperlyConfiguredException);
pyo3::import_exception!(starlite.exceptions, MethodNotAllowedException);
pyo3::import_exception!(starlite.exceptions, NotFoundException);

/// A context object that stores Python handles that are needed in the trie
#[derive(Debug)]
struct StarliteContext {
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

/// A node for the trie
#[derive(Debug, Clone, Default)]
struct Node {
    components: HashSet<String>,
    children: HashMap<String, Node>,
    path_parameters: Option<Vec<HashMap<String, Py<PyAny>>>>,
    asgi_handlers: Option<HashMap<String, Py<PyAny>>>,
    is_asgi: bool,
    static_path: Option<String>,
}

impl Node {
    /// Creates a new trie node
    fn new() -> Self {
        Default::default()
    }
}

impl IntoPy<PyResult<Py<PyDict>>> for &Node {
    /// Converts the Rust representation to a PyDict representation
    fn into_py(self, py: Python) -> PyResult<Py<PyDict>> {
        let dict = PyDict::new(py);

        dict.set_item("components", &self.components)?;

        for (component, node) in &self.children {
            dict.set_item(component, node.into_py(py)?)?;
        }

        if let Some(ref path_parameters) = self.path_parameters {
            dict.set_item("path_parameters", path_parameters)?;
        }

        if let Some(ref asgi_handlers) = self.asgi_handlers {
            dict.set_item("asgi_handlers", asgi_handlers)?;
        }

        dict.set_item("is_asgi", self.is_asgi)?;

        if let Some(ref static_path) = self.static_path {
            dict.set_item("static_path", static_path)?;
        }

        Ok(dict.into())
    }
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
    map: Node,
    static_paths: HashSet<String>,
    plain_routes: HashSet<String>,
    ctx: StarliteContext,
}

// The functions below are available to Python code
#[pymethods]
impl RouteMap {
    /// Creates an empty `RouteMap`
    #[new]
    #[args(debug = false)]
    fn new(py: Python, debug: bool) -> PyResult<Self> {
        let parsers = py.import("starlite.parsers")?;
        let parse_path_params = get_attr_and_downcast(parsers, "parse_path_params")?;

        let routes = py.import("starlite.routes")?;
        let http_route = get_attr_and_downcast(routes, "HTTPRoute")?;
        let web_socket_route = get_attr_and_downcast(routes, "WebSocketRoute")?;
        let asgi_route = get_attr_and_downcast(routes, "ASGIRoute")?;

        let middleware = py.import("starlite.middleware")?;
        let exception_handler_middleware =
            get_attr_and_downcast(middleware, "ExceptionHandlerMiddleware")?;

        let starlette_middleware = py.import("starlette.middleware")?;
        let starlette_middleware = get_attr_and_downcast(starlette_middleware, "Middleware")?;

        Ok(RouteMap {
            map: Node::new(),
            plain_routes: HashSet::new(),
            static_paths: HashSet::new(),
            ctx: StarliteContext {
                http_route,
                web_socket_route,
                asgi_route,
                exception_handler_middleware,
                starlette_middleware,
                parse_path_params,
                debug,
            },
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

    /// Add routes to the map
    fn add_routes(&mut self, py: Python, routes: Vec<&PyAny>) -> PyResult<()> {
        for route in routes {
            let path: String = route.getattr("path")?.extract()?;
            let path_parameters: Vec<HashMap<String, Py<PyAny>>> =
                route.getattr("path_parameters")?.extract()?;

            let cur_node = self.add_node_to_route_map(route, path, &path_parameters[..])?;

            let cur_node_path_parameters = cur_node.path_parameters.as_ref().unwrap();

            if !path_parameters_eq(cur_node_path_parameters, &path_parameters, py)? {
                return Err(ImproperlyConfiguredException::new_err(
                    "Should not use routes with conflicting path parameters",
                ));
            }
        }

        Ok(())
    }

    /// Given a scope, retrieves the correct ASGI App for the route
    fn resolve_asgi_app(&self, scope: &PyAny) -> PyResult<Py<PyAny>> {
        let (asgi_handlers, is_asgi) = self.parse_scope_to_route(scope)?;

        if is_asgi {
            Ok(asgi_handlers.get("asgi").unwrap().clone())
        } else {
            let scope_type: &str = scope.get_item("type")?.extract()?;
            if scope_type == "http" {
                let method: &str = scope.get_item("method")?.extract()?;
                match asgi_handlers.get(method) {
                    Some(handler) => Ok(handler.clone()),
                    None => Err(MethodNotAllowedException::new_err("")),
                }
            } else {
                Ok(asgi_handlers.get("websocket").unwrap().clone())
            }
        }
    }

    /// Given a path, traverses the route map to find the corresponding trie node
    /// and converts it to a `PyDict` before returning
    fn traverse_to_dict(&self, py: Python, path: &str) -> PyResult<Py<PyDict>> {
        let mut cur_node = &self.map;

        if self.is_plain_route(path) {
            cur_node = cur_node.children.get(path).unwrap();
        } else {
            let components = get_base_components(path);
            for component in components {
                let components_set = &cur_node.components;
                if components_set.contains(component) {
                    cur_node = cur_node.children.get(component).unwrap();
                    continue;
                }
                if components_set.contains("*") {
                    cur_node = cur_node.children.get("*").unwrap();
                    continue;
                }
                return Err(NotFoundException::new_err(""));
            }
        }

        cur_node.into_py(py)
    }

    fn __repr__(&self) -> String {
        format!("{:#?}", self)
    }
}

impl Drop for RouteMap {
    fn drop(&mut self) {
        // Avoid recursively dropping nodes, possibly leading to stack overflow, instead, steal their children
        let mut stack = Vec::new();
        stack.extend(self.map.children.drain().map(|(_, node)| node));
        while let Some(mut node) = stack.pop() {
            stack.extend(node.children.drain().map(|(_, node)| node));
        }
    }
}

/// A struct containing values borrowed from a RouteMap instance
/// that are required to run `configure_route_map_node`.
///
/// These are extracted into a struct to allow for clearer passing
/// of parameters, making it more obvious which parts are directly
/// borrowed from the RouteMap, and which are not.
///
/// Creating a method (that takes a ref to self) of RouteMap that takes a
/// `cur_node: &mut Node` is not currently possible, since `cur_node` is mutably borrowed from `self.map`
/// and passed into this method that takes a `&mut self`, so the compiler doesn't know that
/// we won't get another `&mut Node` or `&Node` to the same `Node`.
/// Instead, we just have a struct that stores all the references we'll need and disjointly
/// borrow from the RouteMap to create it and use that.
///
/// Reference: https://smallcultfollowing.com/babysteps/blog/2018/11/01/after-nll-interprocedural-conflicts
struct ConfigureNodeView<'rm> {
    ctx: &'rm StarliteContext,
    static_paths: &'rm HashSet<String>,
    cur_node: &'rm mut Node,
}

impl<'rm> ConfigureNodeView<'rm> {
    /// Set required attributes and route handlers on route_map tree node.
    ///
    /// Note: This method does not use `&self` because it needs to
    /// immutably access other members of `self` while passing a &mut Node
    /// that is mutably borrowed from self.map as a parameter
    fn configure_route_map_node(
        &mut self,
        route: &PyAny,
        path: String,
        path_parameters: &[HashMap<String, Py<PyAny>>],
    ) -> PyResult<()> {
        let py = route.py();

        let ConfigureNodeView {
            ctx,
            static_paths,
            cur_node,
        } = self;

        let StarliteContext {
            http_route,
            web_socket_route,
            asgi_route,
            ..
        } = ctx;

        if cur_node.path_parameters.is_none() {
            cur_node.path_parameters = Some(path_parameters.to_vec());
        }

        if cur_node.asgi_handlers.is_none() {
            cur_node.asgi_handlers = Some(HashMap::new());
        }

        if static_paths.contains(&path[..]) {
            cur_node.static_path = Some(path);
            cur_node.is_asgi = true;
        }

        let asgi_handlers = cur_node.asgi_handlers.as_mut().unwrap();

        let mut generate_single_route_handler_stack = |handler_type: &str| -> PyResult<()> {
            let route_handler = route.getattr("route_handler")?;
            let middleware_stack = build_route_middleware_stack(py, ctx, route, route_handler)?;
            asgi_handlers.insert(handler_type.to_string(), middleware_stack);
            Ok(())
        };

        if route.is_instance(http_route.as_ref(py))? {
            let route_handler_map: HashMap<String, &PyAny> =
                route.getattr("route_handler_map")?.extract()?;

            for (method, handler_mapping) in route_handler_map.into_iter() {
                let handler_mapping = handler_mapping.downcast::<PyTuple>()?;
                let route_handler = handler_mapping.get_item(0)?;
                let middleware_stack = build_route_middleware_stack(py, ctx, route, route_handler)?;
                asgi_handlers.insert(method, middleware_stack);
            }
        } else if route.is_instance(web_socket_route.as_ref(py))? {
            generate_single_route_handler_stack("websocket")?;
        } else if route.is_instance(asgi_route.as_ref(py))? {
            generate_single_route_handler_stack("asgi")?;
            cur_node.is_asgi = true;
        }

        Ok(())
    }
}

// The functions below are not available to Python
impl RouteMap {
    /// Adds a new route path (e.g. '/foo/bar/{param:int}') into the route_map tree.
    ///
    /// Inserts non-parameter paths ('plain routes') off the tree's root node.
    /// For paths containing parameters, splits the path on '/' and nests each path
    /// segment under the previous segment's node (see prefix tree / trie).
    fn add_node_to_route_map(
        &mut self,
        route: &PyAny,
        mut path: String,
        path_parameters: &[HashMap<String, Py<PyAny>>],
    ) -> PyResult<&Node> {
        let py = route.py();

        let mut cur_node;

        if !path_parameters.is_empty() || self.is_static_path(&path[..]) {
            for param_definition in path_parameters {
                let param_definition_full =
                    param_definition.get("full").unwrap().extract::<&str>(py)?;
                path = path.replace(param_definition_full, "");
            }
            path = path.replace("{}", "*");

            cur_node = &mut self.map;

            let components = get_base_components(&path);

            for component in components {
                let component_set = &mut cur_node.components;
                component_set.insert(component.to_string());

                cur_node = cur_node
                    .children
                    .entry(component.to_string())
                    .or_insert_with(Node::new);
            }
        } else {
            self.add_plain_route(&path[..]);
            cur_node = self
                .map
                .children
                .entry(path.clone())
                .or_insert_with(Node::new);
        }

        ConfigureNodeView {
            ctx: &self.ctx,
            static_paths: &self.static_paths,
            cur_node,
        }
        .configure_route_map_node(route, path, path_parameters)?;

        Ok(cur_node)
    }

    /// Given a path and a scope, traverses the route map to find the corresponding trie node
    /// and removes any static path from the scope's stored path
    fn traverse_to_node<'s, 'p>(
        &'s self,
        path: &'p str,
        scope: &PyAny,
    ) -> PyResult<(&'s Node, Vec<&'p str>)> {
        let mut path_params = vec![];
        let mut cur_node = &self.map;

        let components = get_base_components(path);
        for component in components {
            let components_set = &cur_node.components;
            if components_set.contains(component) {
                cur_node = cur_node.children.get(component).unwrap();
                continue;
            }
            if components_set.contains("*") {
                path_params.push(component);
                cur_node = cur_node.children.get("*").unwrap();
                continue;
            }
            if let Some(ref static_path) = cur_node.static_path {
                if static_path != "/" {
                    let scope_path: &str = scope.get_item("path")?.extract()?;
                    scope.set_item("path", scope_path.replace(static_path, ""))?;
                }
                continue;
            }
            return Err(NotFoundException::new_err(""));
        }

        Ok((cur_node, path_params))
    }

    /// Adds a new plain route by path name
    fn add_plain_route(&mut self, path: &str) {
        self.plain_routes.insert(path.to_string());
    }

    /// Checks if a given path refers to a plain route
    fn is_plain_route(&self, path: &str) -> bool {
        self.plain_routes.contains(path)
    }

    /// Given a scope object, and a reference to Starlite's parser function `parse_path_params`,
    /// retrieves the asgi_handlers and is_asgi values from correct trie node.
    ///
    /// Raises `NotFoundException` if no correlating node is found for the scope's path
    fn parse_scope_to_route(&self, scope: &PyAny) -> PyResult<(&HashMap<String, Py<PyAny>>, bool)> {
        let py = scope.py();

        let mut path = scope
            .get_item("path")?
            .extract::<&str>()?
            .trim()
            .to_string();

        if &path[..] != "/" && path.ends_with('/') {
            path = path.strip_suffix('/').unwrap().to_string();
        }

        let cur: &Node;
        let path_params: Vec<&str>;
        if self.is_plain_route(&path) {
            cur = self.map.children.get(&path).unwrap();
            path_params = vec![];
        } else {
            (cur, path_params) = self.traverse_to_node(&path, scope)?;
        }

        let args = match cur.path_parameters {
            Some(ref path_parameter_defs) => (path_parameter_defs.clone(), path_params),
            None => (Vec::<HashMap<String, Py<PyAny>>>::new(), path_params),
        };
        scope.set_item(
            "path_params",
            self.ctx.parse_path_params.as_ref(py).call1(args)?,
        )?;

        if cur.asgi_handlers.is_none() {
            Err(NotFoundException::new_err(""))
        } else {
            let asgi_handlers = cur.asgi_handlers.as_ref().unwrap();
            let is_asgi = cur.is_asgi;

            Ok((asgi_handlers, is_asgi))
        }
    }
}
