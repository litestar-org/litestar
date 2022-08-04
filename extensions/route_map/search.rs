use pyo3::prelude::*;
use std::borrow::Cow;
use std::collections::hash_map::Entry;
use std::collections::HashMap;

use crate::util::normalize_path;
use crate::{get_base_components, util, wrappers, HandlerGroup, Node, RouteMap};

pub(crate) fn find_insert_handler_group(
    root: &mut Node,
    plain_routes: &mut HashMap<String, HandlerGroup>,
    path: &str,
    path_parameters: &PyAny,
    is_static: bool,
    handler_group: HandlerGroup,
) -> PyResult<()> {
    let py = path_parameters.py();
    let path_parameters_vec: Vec<wrappers::PathParameter> = path_parameters.extract()?;
    if !path_parameters_vec.is_empty() || is_static {
        let param_set = util::param_set(&path_parameters_vec)?;
        let mut node = root;
        for s in get_base_components(path) {
            // Could we just assume a path segment that starts and ends
            // with `{}` is a placeholder?
            let is_placeholder =
                s.starts_with('{') && s.ends_with('}') && param_set.contains(&s[1..s.len() - 1]);

            node = if is_placeholder {
                node.placeholder_child
                    .get_or_insert_with(Box::<Node>::default)
            } else {
                node.children
                    .entry(String::from(s))
                    .or_insert_with(Node::default)
            };
        }
        // Found where the handlers should be, get it, or add a new one
        match node.handler_group {
            Some(ref mut existing) => existing.merge(py, handler_group, path)?,
            None => node.handler_group.insert(handler_group),
        }
    } else {
        match plain_routes.entry(String::from(path)) {
            Entry::Occupied(entry) => entry.into_mut().merge(py, handler_group, path)?,
            Entry::Vacant(entry) => entry.insert(handler_group),
        }
    };
    Ok(())
}

impl RouteMap {
    pub(crate) fn find_handler_group(&self, full_path: &str) -> PyResult<FindResult> {
        let mut path = normalize_path(full_path);
        let mut param_values = Vec::new();
        let mut node = &self.root;

        let handler_group: &HandlerGroup = match self.plain_routes.get(path.as_ref()) {
            Some(handler_group) => handler_group,
            None => {
                for component in get_base_components(&path) {
                    if let Some(child) = node.children.get(component) {
                        node = child;
                        continue;
                    }
                    if let Some(child) = &node.placeholder_child {
                        node = child;
                        param_values.push(String::from(component));
                        continue;
                    }
                    let static_path: Option<&str> = node
                        .handler_group
                        .as_ref()
                        .and_then(HandlerGroup::static_path);
                    if let Some(static_path) = static_path {
                        if static_path != "/" {
                            path = Cow::Owned(path.replace(static_path, ""));
                        }
                        break;
                    }

                    return Err(wrappers::NotFoundException::new_err(()));
                }
                node.handler_group
                    .as_ref()
                    .ok_or_else(|| wrappers::NotFoundException::new_err(()))?
            }
        };
        let changed_path = if path != full_path {
            Some(path.into_owned())
        } else {
            None
        };
        Ok(FindResult {
            handler_group,
            param_values,
            changed_path,
        })
    }
}

pub(crate) struct FindResult<'a> {
    pub(crate) handler_group: &'a HandlerGroup,
    pub(crate) param_values: Vec<String>,
    pub(crate) changed_path: Option<String>,
}
