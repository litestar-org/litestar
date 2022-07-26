use std::borrow::Cow;
use std::collections::HashSet;

use pyo3::prelude::*;

use crate::wrappers::PathParameter;

/// Iterator over components of a path (skipping empty components)
pub(crate) fn get_base_components(path: &str) -> Vec<&str> {
    path.split('/').filter(|s| !s.is_empty()).collect()
}

pub(crate) fn normalize_path(path: &str) -> Cow<str> {
    let path = path.trim();
    let path = path.trim_end_matches('/');
    let mut path = if path.is_empty() {
        Cow::Borrowed("/")
    } else if path.contains("//") {
        let mut chars = path.chars();
        let mut prev_char = chars.next().expect("path was not empty");
        let mut res = String::with_capacity(path.len());
        res.push(prev_char);
        for ch in chars {
            if ch == '/' && prev_char == '/' {
                continue;
            }
            prev_char = ch;
            res.push(ch);
        }
        Cow::Owned(res)
    } else {
        Cow::Borrowed(path)
    };
    if !path.starts_with('/') {
        path.to_mut().insert(0, '/');
    }
    path
}

/// Gets a particular attribute from a module and converts it into Python type T
pub(crate) fn get_attr_and_downcast<T>(module: &PyAny, attr: &str) -> PyResult<Py<T>>
where
    for<'py> T: PyTryFrom<'py>,
    for<'py> &'py T: Into<Py<T>>,
{
    Ok(module.getattr(attr)?.downcast::<T>()?.into())
}

pub(crate) fn param_set<'a>(path_parameters: &[PathParameter<'a>]) -> PyResult<HashSet<&'a str>> {
    path_parameters.iter().map(|param| param.full()).collect()
}
