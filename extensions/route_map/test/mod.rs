use crate::{wrappers, HandlerType, Node, RouteMap};
use pyo3::prelude::*;
use pyo3::types::PyList;
use std::collections::{HashMap, HashSet};
use std::fmt::Debug;
use std::hash::Hash;
use std::ptr;

mod init;

fn node_empty(node: &Node) -> bool {
    node.children.is_empty() && node.placeholder_child.is_none() && node.handler_group.is_none()
}

fn assert_keys_eq<K, EK, V>(map: &HashMap<K, V>, expected_keys: &[EK])
where
    K: Debug + Clone + Eq + Hash,
    EK: Clone + Into<K>,
{
    let actual_keys: HashSet<K> = map.keys().cloned().collect();
    let expected_keys: HashSet<K> = expected_keys.iter().cloned().map(Into::into).collect();

    assert_eq!(actual_keys, expected_keys);
}

fn make_route<'a>(py: Python<'a>, path: &str, method: &str) -> PyResult<wrappers::Route<'a>> {
    let module = PyModule::from_code(
        py,
        include_str!("create_route.py"),
        "create_route.py",
        "create_route",
    )?;
    module.call_method1("http_route", (path, method))?.extract()
}

#[test]
fn simple_route() -> PyResult<()> {
    Python::with_gil(|py| -> PyResult<()> {
        let mut route_map = RouteMap::new(py, true)?;
        let routes = vec![
            make_route(py, "/", "get")?,
            make_route(py, "/", "post")?,
            make_route(py, "/a", "get")?,
        ];
        route_map.add_routes(py, routes)?;

        assert_keys_eq(&route_map.plain_routes, &["/", "/a"]);
        assert!(route_map.static_paths.is_empty());
        assert!(node_empty(&route_map.root));

        let base_handlers = &route_map.plain_routes["/"];
        assert_keys_eq(
            &base_handlers.asgi_handlers,
            &[HandlerType::HttpGet, HandlerType::HttpPost],
        );
        assert!(base_handlers.static_path.is_none());
        assert!(!base_handlers.is_asgi);
        assert!(base_handlers
            .path_parameters
            .as_ref(py)
            .eq(PyList::empty(py))
            .unwrap());

        let a_handlers = &route_map.plain_routes["/a"];
        assert_keys_eq(&a_handlers.asgi_handlers, &[HandlerType::HttpGet]);
        assert!(a_handlers.static_path.is_none());
        assert!(!a_handlers.is_asgi);
        assert!(a_handlers
            .path_parameters
            .as_ref(py)
            .eq(PyList::empty(py))
            .unwrap());

        assert!(ptr::eq(
            route_map.find_handler_group("/").unwrap().handler_group,
            base_handlers
        ));

        Ok(())
    })
}

#[test]
fn plain_route_normalize() {
    Python::with_gil(|py| {
        let mut route_map = RouteMap::new(py, true).unwrap();
        let route = make_route(py, "/a/b", "get").unwrap();
        route_map.add_route(py, route).unwrap();

        route_map.find_handler_group("/a/b/").unwrap();
    });
}
