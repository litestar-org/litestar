use std::collections::HashMap;

use pyo3::{prelude::*, types::IntoPyDict};

/// Splits a path on '/' and adds all of the 'components' to a new Vec.
/// '/' itself is the first component by default since a leading slash
/// is required by convention
pub fn get_base_components(path: &str) -> Vec<&str> {
    let path_split = path.split('/');

    let mut components = Vec::<&str>::with_capacity(path_split.size_hint().0 + 1);
    components.push("/");

    path_split
        .filter(|component| !component.is_empty())
        .for_each(|component| components.push(component));

    components
}

/// Given two HashMap slices representing lists of path parameter definition objects,
/// returns whether they are equal. This is just implementing PartialEq, for this type,
/// but with a normal function because a Python instance is required
pub fn path_parameters_eq(
    a: &[HashMap<String, Py<PyAny>>],
    b: &[HashMap<String, Py<PyAny>>],
    py: Python,
) -> PyResult<bool> {
    let mut eq = true;
    if a.len() != b.len() {
        eq = false;
    } else {
        for (a, b) in a.iter().zip(b.iter()) {
            if !a.into_py_dict(py).eq(b.into_py_dict(py))? {
                eq = false;
                break;
            }
        }
    }
    Ok(eq)
}
