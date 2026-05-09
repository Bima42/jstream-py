from jstream._parser import parse_partial


def test_empty_string():
    assert parse_partial("") is None


def test_open_brace_only():
    assert parse_partial("{") is None


def test_single_complete_field():
    assert parse_partial('{"title":"Inception"') == {"title": "Inception"}


def test_one_complete_one_partial():
    result = parse_partial('{"title":"Inception","year":')
    assert result == {"title": "Inception"}


def test_numeric_field():
    assert parse_partial('{"year":2010') == {"year": 2010}


def test_float_field():
    assert parse_partial('{"score":9.3') == {"score": 9.3}


def test_bool_field():
    assert parse_partial('{"active":true') == {"active": True}


def test_null_field():
    assert parse_partial('{"meta":null') == {"meta": None}


def test_complete_list():
    assert parse_partial('{"tags":["a","b"]') == {"tags": ["a", "b"]}


def test_partial_list_includes_complete_items():
    result = parse_partial('{"tags":["a","b"')
    assert result == {"tags": ["a", "b"]}


def test_deeply_nested_includes_complete_inner_fields():
    result = parse_partial('{"outer":{"inner":1}')
    assert result == {"outer": {"inner": 1}}


def test_deeply_nested_partial_includes_inner():
    result = parse_partial('{"outer":{"inner":1')
    assert result == {"outer": {"inner": 1}}


def test_complete_json():
    full = '{"title":"Inception","year":2010}'
    assert parse_partial(full) == {"title": "Inception", "year": 2010}
