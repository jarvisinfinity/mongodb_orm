import inspect
from typing import *
from pydantic import *
from datetime import datetime, UTC

def get_classes_from_module(module_name):
    # Dynamically import the module
    module = __import__(module_name, fromlist=[''])

    # Get all classes defined in the module
    classes = [member for name, member in inspect.getmembers(module, inspect.isclass) if member.__module__ == module.__name__]

    return classes


def register_model(cls):
    try:
        cls.__initialize__()
        print(cls.__name__ + " model registered successfully")
        return True
    except Exception as e:
        print(cls.__name__ + " model registeration failed with error: " + str(e))
        import traceback
        traceback.print_exc()
        raise e


def register_models(classes):
    # Print the names of the classes
    return [register_model(cls) for cls in classes]


def register_all_models(module_name):
    """ This will register all the classes defined in this page with the given module name.
        call this function once at the end of the module, where the classes are defined.

    Args:
        module_name (module_name): `__name__` of the module where the classes are defined.
    """
    # Get all classes defined in the current module
    all_classes = get_classes_from_module(module_name)

    return register_models(all_classes)


current_datetime = lambda: datetime.now(UTC)
