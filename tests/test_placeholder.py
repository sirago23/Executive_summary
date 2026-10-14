def test_scripts_folder_is_importable():
    import importlib.util

    assert importlib.util.find_spec("pytest") is not None
