use crate::RouteMap;
use pyo3::prelude::*;

#[test]
fn init() -> PyResult<()> {
    pyo3::prepare_freethreaded_python();
    Python::with_gil(|py| -> PyResult<()> {
        let mut route_map = RouteMap::new(py, true.into())?;
        route_map.add_routes(py, vec![])?;

        Ok(())
    })?;

    Ok(())
}
