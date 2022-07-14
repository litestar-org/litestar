use crate::util::{get_base_components, path_parameters_eq};

use std::collections::{hash_map, HashMap, HashSet};

use pyo3::{
    prelude::*,
    types::{PyDict, PyFunction, PyTuple, PyType},
};

pyo3::import_exception!(starlite.exceptions, ImproperlyConfiguredException);
pyo3::import_exception!(starlite.exceptions, MethodNotAllowedException);
pyo3::import_exception!(starlite.exceptions, NotFoundException);

/// A context object that stores Python handles that are needed in the trie
struct StarliteContext {
    /// HTTPRoute
    http_route: Py<PyType>,
    /// WebSocketRoute
    web_socket_route: Py<PyType>,
    /// ASGIRoute
    asgi_route: Py<PyType>,
    /// starlite.parsers.parse_path_params
    parse_path_params: Py<PyFunction>,
}

/// A node for the trie
#[derive(Debug, Clone)]
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
    pub fn new() -> Self {
        Self {
            components: HashSet::new(),
            children: HashMap::new(),
            path_parameters: None,
            asgi_handlers: None,
            is_asgi: false,
            static_path: None,
        }
    }

    /// Converts the Rust representation to a PyDict representation
    pub fn as_pydict(&self) -> PyResult<Py<PyDict>> {
        let gil = Python::acquire_gil();
        let dict = PyDict::new(gil.python());

        dict.set_item("components", self.components.clone())?;
        if let Some(ref asgi_handlers) = self.asgi_handlers {
            dict.set_item("asgi_handlers", asgi_handlers)?;
        }

        if let Some(ref path_parameters) = self.path_parameters {
            dict.set_item("path_parameters", path_parameters)?;
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
pub struct RouteMap {
    map: Node,
    static_paths: HashSet<String>,
    plain_routes: HashSet<String>,
    starlite: Py<PyAny>,
    ctx: StarliteContext,
}

// The functions below are available to Python code
#[pymethods]
impl RouteMap {
    /// Creates an empty `RouteMap`
    #[new]
    pub fn new(py: Python, starlite: Py<PyAny>) -> PyResult<Self> {
        macro_rules! get_attr_and_downcast {
            ($module:ident, $attr:expr, $downcast_ty:ty) => {{
                $module.getattr($attr)?.downcast::<$downcast_ty>()?.into()
            }};
        }

        let parsers = py.import("starlite.parsers")?;
        let parse_path_params = get_attr_and_downcast!(parsers, "parse_path_params", PyFunction);

        let routes = py.import("starlite.routes")?;
        let http_route = get_attr_and_downcast!(routes, "HTTPRoute", PyType);
        let web_socket_route = get_attr_and_downcast!(routes, "WebSocketRoute", PyType);
        let asgi_route = get_attr_and_downcast!(routes, "ASGIRoute", PyType);

        Ok(RouteMap {
            map: Node::new(),
            plain_routes: HashSet::new(),
            static_paths: HashSet::new(),
            starlite,
            ctx: StarliteContext {
                http_route,
                web_socket_route,
                asgi_route,
                parse_path_params,
            },
        })
    }

    /// Adds a new static path by path name
    pub fn add_static_path(&mut self, path: &str) {
        self.static_paths.insert(path.to_string());
    }

    /// Checks if a given path refers to a static path
    pub fn is_static_path(&self, path: &str) -> bool {
        self.static_paths.contains(path)
    }

    /// Removes a path from the static path set
    pub fn remove_static_path(&mut self, path: &str) -> bool {
        self.static_paths.remove(path)
    }

    /// Adds a new plain route by path name
    pub fn add_plain_route(&mut self, path: &str) {
        self.plain_routes.insert(path.to_string());
    }

    /// Checks if a given path refers to a plain route
    pub fn is_plain_route(&self, path: &str) -> bool {
        self.plain_routes.contains(path)
    }

    /// Removes a path from the plain route set
    pub fn remove_plain_route(&mut self, path: &str) -> bool {
        self.plain_routes.remove(path)
    }

    /// Add routes to the map
    pub fn add_routes(&mut self, py: Python) -> PyResult<()> {
        let starlite = self.starlite.as_ref(py);

        let routes: Vec<Py<PyAny>> = starlite.getattr("routes")?.extract()?;

        for route in routes {
            let route = route.as_ref(py);

            let path: String = route.getattr("path")?.extract()?;
            let path_parameters: Vec<HashMap<String, Py<PyAny>>> =
                route.getattr("path_parameters")?.extract()?;

            let cur = self.add_node_to_route_map(route, path, &path_parameters[..])?;

            let cur_path_parameters = cur.path_parameters.as_ref().unwrap();

            if !path_parameters_eq(cur_path_parameters, &path_parameters, py)? {
                return Err(ImproperlyConfiguredException::new_err(
                    "Should not use routes with conflicting path parameters",
                ));
            }
        }

        Ok(())
    }

    // Given a scope, retrieves the correct ASGI App for the route
    pub fn resolve_asgi_app(&self, scope: &PyAny) -> PyResult<Py<PyAny>> {
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
    pub fn traverse_to_dict(&self, path: &str) -> PyResult<Py<PyDict>> {
        let mut cur = &self.map;

        if self.is_plain_route(path) {
            cur = cur.children.get(path).unwrap();
        } else {
            let components = get_base_components(path);
            for component in components {
                let components_set = &cur.components;
                if components_set.contains(component) {
                    cur = cur.children.get(component).unwrap();
                    continue;
                }
                if components_set.contains("*") {
                    cur = cur.children.get("*").unwrap();
                    continue;
                }
                return Err(NotFoundException::new_err(""));
            }
        }

        cur.as_pydict()
    }
}

// The functions below are not available to Python
impl RouteMap {
    /// Set required attributes and route handlers on route_map tree node.
    ///
    /// Note: This method does not use `&self` because it needs to
    /// immutably access other members of `self` while passing a &mut Node
    /// that is mutably borrowed from self.map as a parameter
    fn configure_route_map_node(
        starlite: &Py<PyAny>,
        ctx: &StarliteContext,
        route: &PyAny,
        cur: &mut Node,
        path: String,
        path_parameters: &[HashMap<String, Py<PyAny>>],
        static_paths: &HashSet<String>,
    ) -> PyResult<()> {
        let py = route.py();

        let StarliteContext {
            http_route,
            web_socket_route,
            asgi_route,
            ..
        } = ctx;

        if cur.path_parameters.is_none() {
            cur.path_parameters = Some(path_parameters.to_vec());
        }

        if cur.asgi_handlers.is_none() {
            cur.asgi_handlers = Some(HashMap::new());
        }

        if static_paths.contains(&path[..]) {
            cur.static_path = Some(path);
            cur.is_asgi = true;
        }

        let asgi_handlers = cur.asgi_handlers.as_mut().unwrap();

        macro_rules! build_route_middleware_stack {
            ($route:ident, $route_handler:ident) => {{
                starlite.call_method(
                    py,
                    "build_route_middleware_stack",
                    ($route, $route_handler),
                    None,
                )?
            }};
        }

        macro_rules! generate_single_route_handler_stack {
            ($handler_type:expr) => {
                let route_handler = route.getattr("route_handler")?;
                let middleware_stack = build_route_middleware_stack!(route, route_handler);
                asgi_handlers.insert($handler_type.to_string(), middleware_stack.to_object(py));
            };
        }

        if route.is_instance(http_route.as_ref(py))? {
            let route_handler_map: HashMap<String, &PyAny> =
                route.getattr("route_handler_map")?.extract()?;

            for (method, handler_mapping) in route_handler_map.into_iter() {
                let handler_mapping = handler_mapping.downcast::<PyTuple>()?;
                let route_handler = handler_mapping.get_item(0)?;
                let middleware_stack = build_route_middleware_stack!(route, route_handler);
                asgi_handlers.insert(method, middleware_stack.to_object(py));
            }
        } else if route.is_instance(web_socket_route.as_ref(py))? {
            generate_single_route_handler_stack!("websocket");
        } else if route.is_instance(asgi_route.as_ref(py))? {
            generate_single_route_handler_stack!("asgi");
            cur.is_asgi = true;
        }

        Ok(())
    }

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
    ) -> PyResult<&mut Node> {
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

                if let hash_map::Entry::Vacant(e) = cur_node.children.entry(component.to_string()) {
                    e.insert(Node::new());
                }
                cur_node = cur_node.children.get_mut(component).unwrap();
            }
        } else {
            if let hash_map::Entry::Vacant(e) = self.map.children.entry(path.clone()) {
                e.insert(Node::new());
            }
            self.add_plain_route(&path[..]);
            cur_node = self.map.children.get_mut(&path[..]).unwrap();
        }

        Self::configure_route_map_node(
            &self.starlite,
            &self.ctx,
            route,
            cur_node,
            path,
            path_parameters,
            &self.static_paths,
        )?;

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
        let mut cur = &self.map;

        let components = get_base_components(path);
        for component in components {
            let components_set = &cur.components;
            if components_set.contains(component) {
                cur = cur.children.get(component).unwrap();
                continue;
            }
            if components_set.contains("*") {
                path_params.push(component);
                cur = cur.children.get("*").unwrap();
                continue;
            }
            if let Some(ref static_path) = cur.static_path {
                if static_path != "/" {
                    let scope_path: &str = scope.get_item("path")?.extract()?;
                    scope.set_item("path", scope_path.replace(static_path, ""))?;
                }
                continue;
            }
            return Err(NotFoundException::new_err(""));
        }

        Ok((cur, path_params))
    }

    /// Given a scope object, and a reference to Starlite's parser function `parse_path_params`,
    /// retrieves the asgi_handlers and is_asgi values from correct trie node.
    ///
    /// Raises `NotFoundException` if no correlating node is found for the scope's path
    pub fn parse_scope_to_route(
        &self,
        scope: &PyAny,
    ) -> PyResult<(&HashMap<String, Py<PyAny>>, bool)> {
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
