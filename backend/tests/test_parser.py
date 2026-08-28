import pytest

from app.core.parser import (
    extract_code_units,
    get_parser,
)
from app.models.enums import SymbolType


class TestGetParser:
    def test_supported_language(self):
        parser = get_parser("python")
        assert parser is not None

    def test_aliased_language(self):
        assert get_parser("typescript") is not None

    def test_unsupported_language_raises(self):
        with pytest.raises(ValueError):
            get_parser("ruby")


class TestExtractPython:
    def test_extracts_functions_and_classes(self):
        code = '''\
def hello():
    pass

class Foo:
    def method(self):
        return 1
'''
        units = extract_code_units("x.py", code, "python")
        names = {u.symbol_name for u in units}
        types = {u.symbol_type for u in units}
        assert "hello" in names
        assert "Foo" in names
        assert "method" in names
        assert SymbolType.FUNCTION in types
        assert SymbolType.CLASS in types
        assert SymbolType.METHOD in types

    def test_parent_symbol_assignment(self):
        code = '''\
class Foo:
    def bar(self):
        pass
'''
        units = extract_code_units("x.py", code, "python")
        method = next(u for u in units if u.symbol_name == "bar")
        assert method.parent_symbol == "Foo"

    def test_async_function_extraction(self):
        code = "async def fetch():\n    return 1\n"
        units = extract_code_units("x.py", code, "python")
        assert any(u.symbol_name == "fetch" for u in units)

    def test_line_numbers_are_one_based(self):
        code = "\n\ndef foo():\n    pass\n"
        units = extract_code_units("x.py", code, "python")
        foo = next(u for u in units if u.symbol_name == "foo")
        assert foo.start_line == 3
        assert foo.end_line == 4

    def test_source_code_retained(self):
        code = "def foo():\n    return 42\n"
        units = extract_code_units("x.py", code, "python")
        foo = next(u for u in units if u.symbol_name == "foo")
        assert "return 42" in foo.source_code


class TestExtractPythonDocstring:
    def test_extracts_docstring(self):
        code = '''\
def foo():
    """Does a thing."""
    pass
'''
        units = extract_code_units("x.py", code, "python")
        foo = next(u for u in units if u.symbol_name == "foo")
        assert foo.docstring
        assert "Does a thing" in foo.docstring

    def test_returns_none_without_docstring(self):
        code = "def foo():\n    pass\n"
        units = extract_code_units("x.py", code, "python")
        foo = next(u for u in units if u.symbol_name == "foo")
        assert foo.docstring is None


class TestExtractJavaScript:
    def test_function_declaration(self):
        code = "function add(a, b) {\n  return a + b;\n}\n"
        units = extract_code_units("x.js", code, "javascript")
        assert any(u.symbol_name == "add" for u in units)

    def test_class_and_method(self):
        code = '''\
class Greeter {
  greet(name) {
    return "hi " + name;
  }
}
'''
        units = extract_code_units("x.js", code, "javascript")
        names = {u.symbol_name for u in units}
        assert "Greeter" in names
        assert "greet" in names


class TestExtractTypeScript:
    def test_function_and_class(self):
        code = '''\
interface Shape { area(): number }

class Circle implements Shape {
  area(): number {
    return 3.14;
  }
}
'''
        units = extract_code_units("x.ts", code, "typescript")
        names = {u.symbol_name for u in units}
        assert "Circle" in names
        assert "area" in names
