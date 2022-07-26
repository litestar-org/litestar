#[macro_export]
macro_rules! get_routes {
    ($py:ident, $import_from:expr) => {{
        let locals = pyo3::types::PyDict::new($py);
        $py.run(include_str!($import_from), None, Some(locals))?;
        let route = locals.get_item("route").unwrap().to_object($py);
        vec![route]
    }};
}
