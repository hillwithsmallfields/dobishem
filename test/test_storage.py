from collections import defaultdict
from frozendict import frozendict
import os
import pytest
import dobishem.storage

REFERENCE = [ {'Date': "2023-12-09", 'Item': "akullore", 'Price': "1.00"},
              {'Date': "2023-12-09", 'Item': "buke", 'Price': "2.20"},
              {'Date': "2023-12-10", 'Item': "spinaq", 'Price': ".50"},
             ]

REFERENCE_AS_SET = defaultdict(set)
for row in REFERENCE:
    REFERENCE_AS_SET[row['Date']].add(frozendict(row))

DEFAULTS = {}
TEMPLATES = {'by_place': "%(country)s/%(region)s.json"}

def xrow(row):
    return ({'Date': row['Date'],
            'Item': row['Item'],
            'Price': str(1.1 * float(row['Price']))}
            if row['Item'] != "akullore"
            else None)

FILTERED_REFERENCE = [
    xrow(row)
    for row in REFERENCE
    ]

TEMPLATES = {'financial': "%(food_type)s/%(aspect)s.%(fileformat)s"}
TEMPLATE_DEFAULTS = {'fileformat': "csv"}

def test_csv(tmp_path):
    filename = os.path.join(tmp_path, "foo.csv")
    dobishem.storage.default_write_csv(filename, REFERENCE)
    assert dobishem.storage.default_read_csv(filename) == REFERENCE

def test_json(tmp_path):
    filename = os.path.join(tmp_path, "foo.json")
    dobishem.storage.write_json(filename, REFERENCE)
    assert dobishem.storage.read_json(filename) == REFERENCE

def test_yaml(tmp_path):
    filename = os.path.join(tmp_path, "foo.yaml")
    dobishem.storage.write_yaml(filename, REFERENCE)
    assert dobishem.storage.read_yaml(filename) == REFERENCE

def test_generic(tmp_path):
    for extension in ["csv", "json", "yaml"]:
        filename = os.path.join(tmp_path, "foo." + extension)
        dobishem.storage.save(filename, REFERENCE)
        assert dobishem.storage.load(filename) == REFERENCE

def test_csv_set(tmp_path):
    filename = os.path.join(tmp_path, "bar.csv")
    dobishem.storage.default_write_csv(filename, REFERENCE)
    assert dobishem.storage.read_csv(filename,
                                     key_column='Date',
                                     result_type=set) == REFERENCE_AS_SET

def test_filtered_csv(tmp_path):
    filename = os.path.join(tmp_path, "baz.csv")
    dobishem.storage.default_write_csv(filename, REFERENCE)
    assert dobishem.storage.read_csv(filename,
                                     key_column='Date',
                                     transform_row=lambda row: xrow)

def test_storage_class(tmp_path):

    store = dobishem.storage.Storage(templates=TEMPLATES,
                                     defaults=TEMPLATE_DEFAULTS,
                                     base=tmp_path)
    print("resolved " + store.resolve('financial', {'template': 'financial',
                                                    'aspect': 'price',
                                                    'food_type': 'general'}))
    store.save_to(REFERENCE,
                  {'template': 'financial',
                   'aspect': 'price',
                   'fileformat': 'csv',
                   'food_type': 'general'})
    assert store.load_from({'template': 'financial',
                            'aspect': 'price',
                            'food_type': 'general'}) == REFERENCE

@pytest.mark.skip(reason="not working yet; crashes")
def test_using_files(tmp_path):
    def divmod(a, b):
        a, b = int(a), int(b)
        return str(a/b) + "\n", str(a%b) + "\n"
    with open(os.path.join(tmp_path, "seven"), 'w') as outstream:
        outstream.write("7\n")
    with open(os.path.join(tmp_path, "twelve"), 'w') as outstream:
        outstream.write("12\n")
    with dobishem.storage.UsingFiles(["twelve", "seven"],
                                     ["div", "mod"],
                                     {'relative': "%s", 'absolute': "%s"},
                                     {},
                                     base=tmp_path) as filer:
        print("filer is", filer)
        x, y = divmod(*filer)
        # filer.save(x, y)
    with open(os.path.join(tmp_path, "div")) in instream:
        assert instream.read() == "1.7142857142857142\n"
    with open(os.path.join(tmp_path, "mod")) in instream:
        assert instream.read() == "5\n"

def test_template_selection(tmp_path):
    store = dobishem.storage.Storage(templates=TEMPLATES,
                                     defaults=DEFAULTS,
                                     base=tmp_path)
    store.save(REFERENCE, region="Tiranë", country="Shqiperi")
    assert dobishem.storage.read_json(
        os.path.join(tmp_path, "Shqiperi", "Tiranë.json")) == REFERENCE
