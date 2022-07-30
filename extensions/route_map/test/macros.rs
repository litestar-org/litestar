#[macro_export]
macro_rules! get_routes {
    ($py:ident, $import_from:expr) => {{
        let locals = pyo3::types::PyDict::new($py);
        $py.run(include_str!($import_from), None, Some(locals))?;
        let routes = locals
            .get_item("routes")
            .unwrap()
            .downcast::<pyo3::types::PyList>()?
            .extract::<Vec<_>>()?;
        routes
    }};
}
