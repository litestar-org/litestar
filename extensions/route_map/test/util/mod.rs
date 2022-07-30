use crate::util::*;
use pyo3::{prelude::*, types::PyDict};

#[test]
fn get_base_components_root() {
    let path = "/";

    let components = get_base_components(path);

    assert_eq!(components, vec!["/"]);
}

#[test]
fn get_base_components_plain() {
    let path = "/healthcheck";

    let components = get_base_components(path);

    assert_eq!(components, vec!["/", "healthcheck"]);
}

#[test]
fn get_base_components_two() {
    let path = "/articles/new";

    let components = get_base_components(path);

    assert_eq!(components, vec!["/", "articles", "new"]);
}

#[test]
fn get_base_components_one_path_param() {
    let path = "/articles/*";

    let components = get_base_components(path);

    assert_eq!(components, vec!["/", "articles", "*"]);
}

#[test]
fn path_parameters_eq_empty_eq() -> PyResult<()> {
    Python::with_gil(|py| -> PyResult<()> {
        let path_parameters_a = [];
        let path_parameters_b = [];

        let eq = path_parameters_eq(&path_parameters_a, &path_parameters_b, py)?;

        assert!(eq);

        Ok(())
    })
}

#[test]
fn path_parameters_eq_one_eq() -> PyResult<()> {
    Python::with_gil(|py| -> PyResult<()> {
        let locals = PyDict::new(py);
        py.run(
            include_str!("./path_parameters_eq_one_eq.py"),
            None,
            Some(locals),
        )?;
        let parameter1 = locals.get_item("parameter1").unwrap().extract()?;
        let parameter2 = locals.get_item("parameter2").unwrap().extract()?;

        let path_parameters_a = [parameter1];
        let path_parameters_b = [parameter2];

        let eq = path_parameters_eq(&path_parameters_a, &path_parameters_b, py)?;

        assert!(eq);

        Ok(())
    })
}

#[test]
fn path_parameters_eq_one_neq() -> PyResult<()> {
    Python::with_gil(|py| -> PyResult<()> {
        let locals = PyDict::new(py);
        py.run(
            include_str!("./path_parameters_eq_one_neq.py"),
            None,
            Some(locals),
        )?;
        let parameter1 = locals.get_item("parameter1").unwrap().extract()?;
        let parameter2 = locals.get_item("parameter2").unwrap().extract()?;

        let path_parameters_a = [parameter1];
        let path_parameters_b = [parameter2];

        let eq = path_parameters_eq(&path_parameters_a, &path_parameters_b, py)?;

        assert!(!eq);

        Ok(())
    })
}
