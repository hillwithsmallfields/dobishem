# John Sturdy's storage utils

"""Utility functions for reading and writing files.

The writer functions return what they have written,
so can be used in a passthrough manner.

All the functions using filenames expand environment variables and '~'
in the names.
"""

from collections import defaultdict
import csv
import glob
import json
import operator
import os
import re
import yaml
from frozendict import frozendict

def _expand(filename):
    """Expand environment variables and '`~' in a filename."""
    return os.path.expandvars(os.path.expanduser(filename))

def open_for_read(filename, *args, **kwargs):
    """Return an input stream for the named file."""
    return open(_expand(filename), *args, **kwargs)

def open_for_write(filename, *args, **kwargs):
    """Return an output stream to the named file.
    If necessary, create the directory the file is to go into."""
    full_name = _expand(filename)
    os.makedirs(os.path.dirname(full_name), exist_ok=True)
    return open(full_name, 'w', *args, **kwargs)

def read_csv(
        filename,
        result_type=list,
        row_type=dict,
        key_column=None,
        empty_for_missing=True,
        transform_row=None,
):
    """Read a CSV file, returning a structure according to result_type.
    The result types are:
    list: a list of rows (key column is ignored)
    dict: a dictionary of rows, keyed by the key column
    set: a dictionary of sets of rows, keyed by the key column

    The elements of the structure are tuples, lists or dicts,
    according to row_type.

    If a function is given for the transform_row argument, it is
    called on each row, and its result is used instead of the original
    row.  If it returns a false value for a row, that row is not used.
    """
    if not os.path.exists(_expand(filename)):
        if empty_for_missing:
            return result_type()
        raise FileNotFoundError(filename)
    with open_for_read(filename) as instream:
        rows = list(csv.DictReader(instream)
                    if issubclass(row_type, dict)
                    else ((tuple(row) for row in csv.reader(instream))
                          if issubclass(row_type, tuple)
                          else csv.reader(instream)))
        if transform_row:
            rows = [row
                    for raw in rows
                    if (row := transform_row(raw))]
        if issubclass(result_type, set):
            result = defaultdict(set)
            for row in rows:
                result[row[key_column]].add(frozendict(row))
            return result
        return ({row[key_column]: row
                 for row in rows}
                if issubclass(result_type, dict)
                else rows)

def default_read_csv(filename):
    """Read a CSV file as for a list of dated entries."""
    return read_csv(filename, key_column='Date')

def column_headers(table):
    """Return the column headers of a table."""
    return (set().union(*(set(row.keys())
                          for row in table)))

def write_csv(
        filename,
        data,
        flatten=False,
        sort_columns=None,
        silently_skip_missing_data=True,
):
    """Write a CSV file from a list or dict of lists or dicts,
    or, if flatten is true, a dict or list of collections
    of dicts or lists."""
    if sort_columns is None:
        sort_columns = []
    if silently_skip_missing_data and not data:
        return data
    rows_or_groups = (data.values()
                      if isinstance(data, dict)
                      else data)
    rows = list(operator.add([],
                             *(list(row)
                               for row in rows_or_groups))
                if flatten
                else rows_or_groups)
    rows_are_dicts = isinstance(rows[0], dict)
    if sort_columns:
        rows = sorted(rows, key=lambda row: [row.get(k, "") for k in sort_columns])
    with open_for_write(filename) as outstream:
        writer = (csv.DictWriter(outstream,
                                 fieldnames=(sort_columns
                                             + sorted(column_headers(rows)
                                                 - set(sort_columns))))
                  if rows_are_dicts
                  else csv.writer(outstream))
        if rows_are_dicts:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return data

def default_write_csv(filename, data):
    """Write a CSV file as for a list of dated entries."""
    columns = column_headers(data)
    return write_csv(
        filename, data,
        # Use whichever likely sort columns are present in the data
        sort_columns=[col
                      for col in ["Date", "Time", "Account", "Item", "Details"]
                      if col in columns])

def read_json(filename):
    """Read a JSON file."""
    with open_for_read(filename) as instream:
        return json.load(instream)

def write_json(filename, data):
    """Write a JSON file."""
    with open_for_read(filename, 'w') as outstream:
        json.dump(data, outstream)
    return data

def read_yaml(filename):
    """Read a YAML file."""
    with open_for_read(filename) as instream:
        return yaml.safe_load(instream)

def write_yaml(filename, data):
    """Write a YAML file."""
    with open_for_read(filename, 'w') as outstream:
        yaml.dump(data, outstream)
    return data

READERS = {
    ".csv": default_read_csv,
    ".json": read_json,
    ".yaml": read_yaml,
    }

WRITERS = {
    ".csv": default_write_csv,
    ".json": write_json,
    ".yaml": write_yaml,
    }

def load(
        filename,
        verbose=False,
        messager=None,
):
    """Read a file, finding a suitable reader function for the filename."""
    if verbose:
        if messager:
            messager.print(f"Reading {filename}")
        else:
            print("Reading", filename)
    return READERS[os.path.splitext(filename)[1]](filename)

def save(
        filename,
        data,
        verbose=False,
        messager=None,
):
    """Write a file, finding a suitable writer function for the filename."""
    if verbose:
        if messager:
            messager.print(f"Writing {filename}")
        else:
            print("Writing", filename)
    return WRITERS[os.path.splitext(filename)[1]](filename, data)

class DirectoryIter:

    def __init__(self, directory):
        self.directory = directory
        self.files = directory.contents.copy()

    def __iter__(self):
        return self

    def __next__(self):
        if self.files:
            name = self.files.pop()
            return name, self.directory.storage.load(self.directory.template, name)
        raise StopIteration

class DirectoryAsDictionary:

    def __init__(self, storage, template, dirname):
        self.storage = storage
        self.template = template
        self.dirname = dirname
        self.contents = sorted(os.listdir(dirname))

    def __iter__(self):
        return DirectoryIter(self)

    def items(self):
        return self.__iter__()

    def __getitem__(self, value):
        pass

    def __setitem__(self, key, value):
        pass

    def __contains__(self, key):
        pass

    def update(self, mapping):
        pass

class Storage:

    """A storage handler class,
    providing templated filename generation from named parts.

    If no template is specified (or the template is `True`)
    one is chosen by the combination of location keys used."""

    def __init__(
            self,
            templates,
            defaults,
            base="."):
        self.templates = templates
        self.templates_by_keys = {
            ":".join(sorted(re.findall(r'%\(([a-z_0-9]+)\)', template))): template
            for template in self.templates.values()}
        self.defaults = defaults
        self.base = base

    def get_template(self, template_name, kwargs):
        """Look up an explictly specified template by name,
        or deduce one from the keys used."""
        return (self.templates_by_keys[":".join(sorted(kwargs.keys()))]
                if template_name is True
                else self.templates.get(template_name, 'default'))

    def resolve(self,
                template,
                kwargs):
        """Resolve a location to a filename string."""
        return _expand(
            os.path.join(self.base,
                         self.get_template(template, kwargs) % (self.defaults | kwargs)))

    @staticmethod
    def _get_template(raw):
        return ('absolute' if os.path.isabs(raw) else 'relative') if isinstance(raw, str) else raw.get('template', True)

    @staticmethod
    def _get_location(raw):
        return {'str': raw} if isinstance(raw, str) else {k: v for k, v in raw.items() if k != 'template'}

    def glob(self, pattern, template, **kwargs):
        return glob.glob(self.resolve(template, kwargs)+pattern)

    def open_for_read(self, template, **kwargs):
        return open_for_read(self.resolve(template, kwargs))

    def open_for_write(self, template, **kwargs):
        return open_for_write(self.resolve(template, kwargs))

    def load(self, template, **kwargs):
        return load(self.resolve(template, kwargs))

    def load_from(self, location):
        return self.load(location.get('template', True),
                         **self._get_location(location))

    def save(self, data, template, **kwargs):
        return save(self.resolve(template, kwargs),
                    data)

    def save_to(self, data, location):
        return self.save(data,
                         location.get('template', True),
                         **self._get_location(location))

class UsingFiles(Storage):

    def __init__(self, inputs, outputs, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.inputs = inputs
        self.outputs = outputs

    def __iter__(self):
        print("UsingFiles return self as iterator with inputs", self.inputs, "and outputs", self.outputs)
        return self

    def __next__(self):
        for location in self.inputs:
            print("input location", location)
            yield self.load_from(location)
        raise StopIteration

    def save(self, *values):
        for location, content in zip(self.outputs, values).items():
            print("writing to", location)
            self.save_to(content, location)

    def __enter__(self):
        print("UsingFiles entering with inputs", self.inputs, "and outputs", self.outputs)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            print("exception", exc_type, exc_value)

def function_cached_with_file(function, filename):
    """Read a file and return its contents.
    If the file does not exist, run a function to create the contents,
    write them to the file, and return them."""
    filename = _expand(filename)
    return (load(filename)
            if os.path.exists(filename)
            else save(filename, function()))

def modified(filename):
    """Return the modification time of a file.
    If the file does not exist, the epoch is returned."""
    if filename is None:
        return 0
    fname = _expand(filename)
    return os.path.getmtime(fname) if os.path.exists(fname) else 0

def file_newer_than_file(a, b):
    return os.path.getmtime(_expand(a)) > os.path.getmtime(_expand(b))

def in_modification_order(filenames):
    """"Return a list of filenames sorted into modification order.
    If the filenames are given as a string rather than a list,
    apply shell-style globbing to convert it to a list."""
    if isinstance(filenames, str):
        filenames = glob.glob(_expand(filenames))
    return sorted(filenames, key=modified)

def most_recently_modified(filenames):
    """Return the most recently modified of a list of files."""
    names = in_modification_order(filenames)
    return names[-1] if names else None

def combined(
        destination,
        combiner,
        origins,
        reloader=lambda x: x,
        verbose=False,
        messager=None,
):
    """If any of the origin files have been updated since the destination
    was, run the combiner function on their contents and write its
    result to the destination, returning the result.

    The 'combiner' argument is a function taking a list of lists,
    typically, the result of reading multiple CSV files, and its
    result would typically be a list to be written to a CSV file.

    The 'origins' argument is a dictionary binding filename strings to
    row processing functions, so this function can be used to
    transform incoming data and merge it into a collection.  If a row
    processing function returns `None`, the row is skipped.

    Otherwise, read and return the destination file, applying the
    'reloader' argument to each entry in it.
    """
    return (save(destination,
                 combiner([[entry
                            for raw in load(origin,
                                            verbose=verbose,
                                            messager=messager)
                            if (entry := converter(raw)) is not None]
                           for origin, converter in origins.items()]),
                 verbose=verbose,
                 messager=messager)
            if (modified(destination)
                < modified(most_recently_modified(origins)))
            else [reload_entry
                  for reload_raw in load(destination,
                                         verbose=verbose,
                                         messager=messager)
                  if (reload_entry := reloader(reload_raw))])

class FileProtection:

    """Check how a file size has changed in this context.

    If it has reduced too much, restore the original contents."""

    def __init__(self, filename, max_reduction=0.1):
        self.filename = filename
        self.max_reduction = max_reduction
        self.data = None

    def __enter__(self):
        with open(self.filename, 'rb') as original:
            self.data = original.read()

    def __exit__(self, exc_type, exc_value, traceback):
        if os.stat(self.filename).st_size < (len(self.data) * self.max_reduction):
            with open(self.filename, 'wb') as restoration:
                restoration.write(self.data)
