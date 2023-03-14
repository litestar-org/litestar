test
====


.. change:: Validation of controller route handler methods
    :type: feature
    :breaking:
    :pr: 1144
    :issue: 921

    Starlite will now validate that no duplicate handlers (that is, they have the same
    path and same method) exist.

