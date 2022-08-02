use crate::test::{assert_keys_eq, node_empty};
use crate::{HandlerGroup, HandlerType, RouteMap};
use pyo3::prelude::*;
use pyo3::types::PyList;

use super::make_route;

#[test]
fn init_empty() -> PyResult<()> {
    Python::with_gil(|py| -> PyResult<()> {
        let mut route_map = RouteMap::new(py, false)?;

        route_map.add_routes(py, Vec::new())?;

        assert!(node_empty(&route_map.root));
        assert!(route_map.static_paths.is_empty());
        assert!(route_map.plain_routes.is_empty());

        Ok(())
    })
}

#[test]
fn init_one_route() -> PyResult<()> {
    Python::with_gil(|py| -> PyResult<()> {
        let mut route_map = RouteMap::new(py, false)?;

        let route = make_route(py, "/test", "get")?;

        route_map.add_route(py, route)?;

        assert!(node_empty(&route_map.root));
        assert!(route_map.static_paths.is_empty());

        assert_keys_eq(&route_map.plain_routes, &["/test"]);

        let handler_group = &route_map.plain_routes["/test"];
        match handler_group {
            HandlerGroup::NonAsgi {
                path_parameters,
                asgi_handlers,
            } => {
                assert_keys_eq(asgi_handlers, &[HandlerType::HttpGet]);
                assert!(path_parameters.as_ref(py).eq(PyList::empty(py)).unwrap());
            }
            _ => panic!("Expected NonAsgi handler group"),
        }

        Ok(())
    })
}

#[test]
fn init_one_deep_path() {
    Python::with_gil(|py| {
        let mut route_map = RouteMap::new(py, false).unwrap();
        let mut path = vec!["a"; 50_000].join("/");
        // Ensure path has a placeholder
        path.insert_str(0, "/{x:str}/");
        let route = make_route(py, &path, "get").unwrap();

        route_map.add_route(py, route).unwrap();
        drop(route_map);
    });
}

#[test]
fn init_one_route_with_path() -> PyResult<()> {
    Python::with_gil(|py| -> PyResult<()> {
        let mut route_map = RouteMap::new(py, false)?;

        let route = make_route(py, "/articles/{id:str}", "get")?;

        route_map.add_route(py, route)?;

        assert!(route_map.static_paths.is_empty());
        assert!(route_map.plain_routes.is_empty());

        let node = &route_map.root;
        assert!(node.handler_group.is_none());
        assert!(node.placeholder_child.is_none());
        assert_keys_eq(&node.children, &["articles"]);

        let node = &node.children["articles"];
        assert!(node.handler_group.is_none());
        assert!(node.children.is_empty());

        let node = node.placeholder_child.as_deref().unwrap();
        assert!(node.children.is_empty());
        assert!(node.placeholder_child.is_none());

        let handler_group = node.handler_group.as_ref().unwrap();
        match handler_group {
            HandlerGroup::NonAsgi {
                path_parameters,
                asgi_handlers,
            } => {
                assert_keys_eq(asgi_handlers, &[HandlerType::HttpGet]);
                assert_eq!(path_parameters.as_ref(py).len().unwrap(), 1);
            }
            _ => panic!("expected NonAsgi Handler Group"),
        }

        Ok(())
    })
}
