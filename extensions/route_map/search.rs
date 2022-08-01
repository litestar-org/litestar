use pyo3::prelude::*;
use std::borrow::Cow;
use std::collections::HashMap;

use crate::util::normalize_path;
use crate::{get_base_components, util, wrappers, HandlerGroup, Node, RouteMap};

pub(crate) fn find_insert_handler_group<'a>(
    root: &'a mut Node,
    plain_routes: &'a mut HashMap<String, HandlerGroup>,
    path: &str,
    path_parameters: &PyAny,
    is_static: bool,
) -> PyResult<&'a mut HandlerGroup> {
    let path_parameters_vec: Vec<wrappers::PathParameter<'_>> = path_parameters.extract()?;
    let handler_group: &mut HandlerGroup = if !path_parameters_vec.is_empty() || is_static {
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
        node.handler_group
            .get_or_insert_with(|| HandlerGroup::new(path_parameters.into()))
    } else {
        plain_routes
            .entry(String::from(path))
            .or_insert_with(|| HandlerGroup::new(path_parameters.into()))
    };
    Ok(handler_group)
}

impl RouteMap {
    pub(crate) fn find_handler_group<'a>(&'a self, full_path: &'a str) -> PyResult<FindResult<'a>> {
        let mut path = normalize_path(full_path);
        let mut param_values = Vec::new();
        let mut node = &self.root;

        let handler_group: &HandlerGroup =
            if let Some(handler_group) = self.plain_routes.get(path.as_ref()) {
                handler_group
            } else {
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
                    let static_path = node
                        .handler_group
                        .as_ref()
                        .and_then(|handler_group| handler_group.static_path.as_deref());
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
