//! A route mapping data structure for use in Starlite

mod route_map;
mod util;

use crate::route_map::RouteMap;

use pyo3::prelude::*;

#[pymodule]
fn route_map_rs(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_class::<RouteMap>()?;
    Ok(())
}
