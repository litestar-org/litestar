use crate::RouteMap;
use pyo3::prelude::*;
use std::collections::HashSet;

mod init;

fn make_route<'a>(py: Python<'a>, path: &str, method: &str) -> PyResult<&'a PyAny> {
    let module = PyModule::from_code(
        py,
        include_str!("create_route.py"),
        "create_route.py",
        "create_route",
    )?;
    module.call_method1("http_route", (path, method))
}

#[test]
fn simple_route() -> PyResult<()> {
    Python::with_gil(|py| -> PyResult<()> {
        let mut route_map = RouteMap::new(py, true.into())?;
        let routes = vec![
            make_route(py, "/", "get")?,
            make_route(py, "/", "post")?,
            make_route(py, "/a", "get")?,
        ];
        route_map.add_routes(py, routes)?;

        assert!(route_map.is_plain_route("/"));
        assert!(route_map.is_plain_route("/a"));
        assert_eq!(
            route_map.plain_routes,
            HashSet::from([String::from("/"), String::from("/a")])
        );
        assert!(!route_map.is_static_path("/"));
        assert_eq!(route_map.static_paths, HashSet::new());

        assert_eq!(route_map.map.components, HashSet::new());
        assert!(route_map.map.path_parameters.is_none());
        assert!(route_map.map.asgi_handlers.is_none());
        assert!(!route_map.map.is_asgi);
        assert!(route_map.map.static_path.is_none());
        assert_eq!(route_map.map.children.len(), 2);

        let root_node = &route_map.map.children["/"];
        assert_eq!(root_node.components, HashSet::new());
        assert_eq!(root_node.path_parameters.as_ref().unwrap().len(), 0);
        assert!(!root_node.is_asgi);
        assert!(root_node.static_path.is_none());

        let asgi_handlers = root_node.asgi_handlers.as_ref().unwrap();
        assert_eq!(asgi_handlers.len(), 2);
        assert!(asgi_handlers.contains_key("GET"));
        assert!(asgi_handlers.contains_key("POST"));

        let a_node = &route_map.map.children["/a"];
        assert_eq!(a_node.components, HashSet::new());
        assert_eq!(a_node.path_parameters.as_ref().unwrap().len(), 0);
        assert!(!a_node.is_asgi);
        assert!(a_node.static_path.is_none());

        let asgi_handlers = a_node.asgi_handlers.as_ref().unwrap();
        assert_eq!(asgi_handlers.len(), 1);
        assert!(asgi_handlers.contains_key("GET"));

        Ok(())
    })
}
