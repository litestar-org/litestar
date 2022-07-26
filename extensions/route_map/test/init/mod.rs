use crate::RouteMap;
use pyo3::prelude::*;

use crate::get_routes;

#[test]
fn init_empty() -> PyResult<()> {
    Python::with_gil(|py| -> PyResult<()> {
        let mut route_map = RouteMap::new(py, false.into())?;

        route_map.add_routes(py, vec![])?;

        let map = &route_map.map;

        assert!(map.components.is_empty());
        assert!(map.children.is_empty());
        assert!(map.path_parameters.is_none());
        assert!(map.asgi_handlers.is_none());
        assert!(!map.is_asgi);
        assert!(map.static_path.is_none());

        Ok(())
    })
}

#[test]
fn init_one_route() -> PyResult<()> {
    Python::with_gil(|py| -> PyResult<()> {
        let mut route_map = RouteMap::new(py, false.into())?;

        let routes = get_routes!(py, "./init_one_route.py");

        route_map.add_routes(py, routes)?;

        let map = &route_map.map;

        assert!(map.components.is_empty());

        assert!(!map.children.is_empty());
        assert_eq!(map.children.len(), 1);
        assert!(map.children.contains_key("/test"));

        {
            let map = map.children.get("/test").unwrap();
            assert!(map.path_parameters.is_some());
            assert!(map.asgi_handlers.is_some());
            if let Some(asgi_handlers) = map.asgi_handlers.as_ref() {
                assert!(asgi_handlers.contains_key("GET"));
            }
        }

        assert!(map.path_parameters.is_none());
        assert!(map.asgi_handlers.is_none());
        assert!(!map.is_asgi);
        assert!(map.static_path.is_none());

        Ok(())
    })
}

#[test]
fn init_one_route_with_path() -> PyResult<()> {
    Python::with_gil(|py| -> PyResult<()> {
        let mut route_map = RouteMap::new(py, false.into())?;

        let routes = get_routes!(py, "./init_one_route_with_path.py");

        route_map.add_routes(py, routes)?;

        let map = &route_map.map;

        assert_eq!(map.components.len(), 1);
        assert!(map.components.contains("/"));

        assert_eq!(map.children.len(), 1);
        assert!(map.children.contains_key("/"));

        // '/'
        {
            let map = map.children.get("/").unwrap();

            assert_eq!(map.components.len(), 1);
            assert!(map.components.contains("articles"));

            assert_eq!(map.children.len(), 1);
            assert!(map.children.contains_key("articles"));

            // 'articles'
            {
                let map = map.children.get("articles").unwrap();

                assert_eq!(map.components.len(), 1);
                assert!(map.components.contains("*"));

                assert_eq!(map.children.len(), 1);
                assert!(map.children.contains_key("*"));

                // '*'
                {
                    let map = map.children.get("*").unwrap();

                    assert!(map.components.is_empty());

                    assert!(map.children.is_empty());

                    assert!(map.asgi_handlers.is_some());

                    if let Some(asgi_handlers) = map.asgi_handlers.as_ref() {
                        assert!(asgi_handlers.contains_key("GET"));
                    }
                }
            }
        }

        assert!(map.path_parameters.is_none());
        assert!(map.asgi_handlers.is_none());
        assert!(!map.is_asgi);
        assert!(map.static_path.is_none());

        Ok(())
    })
}
