import os

# this is required to ensure that piccolo discovers its conf without throwing.
os.environ["PICCOLO_CONF"] = "tests.unit.test_plugins.piccolo_conf"
