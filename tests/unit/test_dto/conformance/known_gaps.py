KNOWN_GAPS: dict[str, str] = {
    "constraint_partial_length-py-in": 'in invalid: expected 400, got 201 {"value": "ab"}',
    "constraint_partial_number-py-in": 'in invalid: expected 400, got 201 {"value": 0}',
    "partial_nested_list-dc-in": 'in full_item: expected 201 {"children": [{"label": "l", "size": 1}]}, got 201 {"children": [{"$model": "Child", "label": "l", "size": 1}]}\nin partial_item: expected 201 {"children": [{"size": 1}]}, got 500',
    "partial_nested_list-ms-in": 'in full_item: expected 201 {"children": [{"label": "l", "size": 1}]}, got 201 {"children": [{"$model": "Child", "label": "l", "size": 1}]}\nin partial_item: expected 201 {"children": [{"size": 1}]}, got 500',
    "partial_nested_list-py-in": 'in full_item: expected 201 {"children": [{"label": "l", "size": 1}]}, got 201 {"children": [{"$model": "Child", "label": "l", "size": 1}]}\nin partial_item: expected 201 {"children": [{"size": 1}]}, got 400',
}
