# John Sturdy's storage utils

"""Utility functions for reading and writing files.

The writer functions return what they have written,
so can be used in a passthrough manner.

All the functions using filenames expand environment variables and '~'
in the names.
"""

import csv
import glob
import json
import os
import re
import tempfile
import yaml

from collections import defaultdict
from frozendict import frozendict

import dobishem.tabular_text

def _expand(filename):
    """Expand environment variables and '`~' in a filename."""
    return os.path.expandvars(os.path.expanduser(filename))

class DirectoryHandler:

    def __init__(self, filename, readable=True, writable=False):
        self.filename = filename
        self.readable = readable
        self.writable = writable

        def __iter__(self):
            pass                # TODO

        def __contains__(self, key):
            # if not self.readable:
            #     raise ....
            pass                # TODO

        def __getitem__(self, key):
            # if not self.readable:
            #     raise ....
            pass                # TODO

        def __setitem__(self, key, value):
            # if not self.writable:
            #     raise ....
            pass                # TODO

        def update(self, incoming):
            pass                # TODO

        def __ior__(self, other):
            pass                # TODO

def open_for_read(filename, *args, **kwargs):
    """Return an input stream for the named file."""
    full_name = _expand(filename)
    return (DirectoryHandler(full_name)
            if os.path.isdir(full_name)
            else open(full_name, *args, **kwargs))

def open_for_write(filename, *args, direction='w', **kwargs):
    """Return an output stream to the named file.
    If necessary, create the directory the file is to go into."""
    full_name = _expand(filename)
    os.makedirs(os.path.dirname(full_name), exist_ok=True)
    return (DirectoryHandler(full_name,
                             readable=(direction!='w'),
                             writable=True)
            if os.path.isdir(full_name)
            else open(full_name, direction, *args, **kwargs))

def open_for_append(filename, *args, **kwargs):
    """Return an output stream to append to the named file.
    If necessary, create the directory the file is to go into."""
    return open_for_write (filename, *args, direction='a', **kwargs)

def row_key(key_column, row):
    """Return a key for the given row, according to the key_column.

    The key_column may be:

    - a name, if the row is a dictionary (as from csv.DictReader)

    - an integer, if the row is a list (as from csv.reader)

    - a tuple or list of names or integers, in which case the key is a
      tuple of those column values, in that order

    - a function, which is applied to the row to get the key

    - - if the row is a dictionary, it is exploded into separate
        arguments with ** (in which case the function should have the
        same argument names as the column names, and discard extra
        columns with **_);

    - - otherwise the row is passed to the function as its only
        argument
    """
    return ((key_column(**row)
             if isinstance(row, dict)
             else key_column(row))
            if callable(key_column)
            else ((tuple(row[k] for k in key_column)
                   if isinstance(key_column, (tuple, list))
                   else row[key_column])))

def strip_row(row, key_column=None, remove_blanks=False):
    """Return a stripped row.

    If key_column is given, it is removed from the row.

    If remove_blanks is given, cells blank strings are omitted from
    the result if it is a dictionary, or replaced with None if it is
    list.
    """
    return ({k: v
             for k, v in row.items()
             if not ((key_column and k == key_column)
                     or (remove_blanks and v == ""))}
            if isinstance(row, dict)
            else [(k if k != "" else None) if remove_blanks else k
                  for i, k in enumerate(row)
                  if i != key_column])

def read_csv(
        filename,
        result_type=list,
        row_type=dict,
        key_column=None,
        strip_key=False,
        remove_blanks=False,
        empty_for_missing=True,
        transform_row=None,
):
    """Read a CSV file, returning a structure according to result_type.

    The possible result types are:

    list: a list of rows (key column is ignored)
    dict: a dictionary of rows, keyed by the key column
    set:  a dictionary of sets of rows, keyed by the key column;
          the rows in each set have the same key, for example all the
          transactions on the same date; each row is a frozendict

    The elements of the structure are tuples, lists or dicts (or
    frozendict, for the set type, as it has to be something that can
    be put into sets), according to row_type.

    If strip_key is given, the key data is removed from each row.

    If remove_blanks is given, cells blank strings are omitted from
    the result if it is a dictionary, or replaced with None if it is
    list.

    The key_column can be a string naming a column if the row_type is
    dict or set, or a number if the row_type is list or tuple; see
    documentation of row_key for further possibilities.

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
                result[row_key(key_column, row)].add(
                    frozendict(strip_row(row,
                                         key_column=strip_key and key_column,
                                         remove_blanks=remove_blanks))
                    if issubclass(row_type, dict)
                    else tuple(row))
            return result
        return ({row_key(key_column, row): strip_row(row,
                                                     key_column=strip_key and key_column,
                                                     remove_blanks=remove_blanks)
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
        sort_columns=None,
        silently_skip_missing_data=True,
):
    """Write a CSV file from a list or dict of lists or dicts.
    Returns the data, so it can be used as a pass-through function.

    If sort_columns is given, it controls the order in which the rows
    appear in the file.  It can be a list of column names used to
    construct a sorting key, or a function to apply to each row to
    create the sorting key.

    If silently_skip_missing_data is given, if the data is empty, no
    file is written (leaving any previous file of that name
    undisturbed).
    """
    if sort_columns is None:
        sort_columns = []
    if silently_skip_missing_data and not data:
        return data
    rows = (data.values()
            if isinstance(data, dict)
            else data)
    rows_are_dicts = any(dict_rows := [isinstance(row, dict) for row in rows])
    if rows_are_dicts:
        assert all(dict_rows)
    if sort_columns:
        rows = sorted(rows, key=(sort_columns
                                 if callable(sort_columns)
                                 else lambda row: [row.get(k, "")
                                                   for k in sort_columns]))
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
    with open_for_write(filename) as outstream:
        json.dump(data, outstream)
    return data

def read_yaml(filename):
    """Read a YAML file."""
    with open_for_read(filename) as instream:
        return yaml.safe_load(instream)

def write_yaml(filename, data):
    """Write a YAML file."""
    with open_for_write(filename) as outstream:
        yaml.dump(data, outstream)
    return data

def read_orgtable(filename):
    """Read an orgtable file."""
    with open_for_read(filename) as instream:
        data, _colnames = dobishem.tabular_text.read_tabular_to_dicts(instream)
        return list(data)

def write_orgtable(filename, data):
    """Write an orgtable file."""
    with open_for_write(filename) as outstream:
        outstream.write(dobishem.tabular_text.dicts_to_tabular_string(data))
    return data

READERS = {
    ".csv": default_read_csv,
    ".json": read_json,
    ".yaml": read_yaml,
    ".table": read_orgtable,
    }

WRITERS = {
    ".csv": default_write_csv,
    ".json": write_json,
    ".yaml": write_yaml,
    ".table": write_orgtable,
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

TEMPLATE_PARAM_RE = re.compile("%\\(([a-zA-Z0-9_]+)\\)")

class Storage:

    """A storage handler class,
    providing templated filename generation from named parts.

    The templates are Python %-substitution strings with named
    substitution parameters, and the parameter names should match the
    kwargs given to methods such as resolve, load, and save.

    For example, a template for a postal address could be:

    "%(housenumber)d %(street)s, %(city)s, %(county)s"

    Templates are chosen to support the kwargs supplied to the methods
    that use them.
    """

    def __init__(
            self,
            templates,
            defaults,
            base="."):
        self.templates = {}
        self.templates_by_params = {}
        for name, template in templates.items():
            self.add_template(name, template)
        print(len(self.templates), "templates by name;", len(self.templates_by_params), "by params")
        self.defaults = defaults
        self.base = base

    def add_template(self, name, template):
        """Add a named template to this storage handler."""
        self.templates[name] = template
        key = self._key_for_template(template)
        if key in self.templates_by_params:
            print("Warning: template already defined for", key)
        self.templates_by_params[key] = template

    def resolve(self,
                **kwargs):
        """Return the filename string made from the selected template."""
        return _expand(
            os.path.join(
                self.base,
                self.template_for_kwargs(kwargs) % (self.defaults | kwargs)))

    def glob(self, pattern, **kwargs):
        """Return the names of files matching the instantiated template
        for the given kwargs."""
        return glob.glob(os.path.join(self.resolve(**kwargs), pattern))

    def template_for_kwargs(self, kwargs):
        """Choose a template that uses the given parameters."""
        key = self._params_key(kwargs.keys())
        if key not in self.templates_by_params:
            print("Key", key, "not found in template collection")
            print("Available templates are:")
            for k in sorted(self.templates_by_params.keys()):
                print(k, "-->", self.templates_by_params[k])
            raise KeyError("Template for %s not defined" % key)
        return self.templates_by_params[key]

    @staticmethod
    def _params_key(param_names):
        """Return the key for a collection of parameter names."""
        return ":".join(sorted(param_names))

    def _key_for_template(self, template):
        """Make a key from the parameters used in a template.
        This is used for finding a template to match the given parameters."""
        return self._params_key([param.group(1)
                                 for param in TEMPLATE_PARAM_RE.finditer(template)])

    def open_for_read(self, **kwargs):
        """Return a file handle suitable for reading."""
        return open_for_read(self.resolve(**kwargs))

    def open_for_write(self, **kwargs):
        """Return a file handle suitable for writing.
        The directory containing the file will have been created if necessary."""
        return open_for_write(self.resolve(**kwargs))

    def load(self, **kwargs):
        """Read a file using templated name resolution and the generic load function from this module."""
        return load(self.resolve(**kwargs))

    def save(self, data, **kwargs):
        """Write a file using templated name resolution and the generic save function from this module."""
        return save(self.resolve(**kwargs),
                    data)

class UsingFiles(Storage):

    """A class to iterate over input and output files.

    Contrived example:

    filer = UsingFiles(inputs=("in0.json", "in1.csv", "in2.yaml"),
                       outputs=("out0.csv", "out1.yaml"))
    filer.save(*my_function(*filer))
    """

    def __init__(self, inputs, outputs, **kwargs):
        super().__init__(**kwargs)
        self.inputs = inputs
        self.outputs = outputs

    def __next__(self):
        for location in self.inputs:
            yield self.load(location)

    def save(self, *values):
        for location, content in zip(self.outputs, values):
            self.save(content, location)

def function_cached_with_file(function, filename):
    """Read a file and return its contents.
    If the file does not exist, run a function to create the contents,
    write them to the file, and return them."""
    return (load(filename)
            if os.path.exists(filename := _expand(filename))
            else save(filename, function()))

def modified(filename):
    """Return the modification time of a file.
    If the file does not exist, the epoch is returned."""
    return (0
            if filename is None
            else (os.path.getmtime(fname)
                  if os.path.exists(fname := _expand(filename))
                  else 0))

def file_newer_than_file(this, that):
    """Compare dates of file updates.

    Returns whether the file named by the first argument has been
    updated more recently than the one named by the second argument.
    """
    return os.path.getmtime(_expand(this)) > os.path.getmtime(_expand(that))

def in_modification_order(filenames):
    """"Return a list of filenames sorted into modification order.
    If the filenames are given as a string rather than a list,
    apply shell-style globbing to convert it to a list."""
    return sorted((glob.glob(_expand(filenames))
                   if isinstance(filenames, str)
                   else filenames),
                  key=modified)

def most_recently_modified(filenames):
    """Return the most recently modified of a list of files."""
    names = in_modification_order(filenames)
    return names[-1] if names else None

def make(
        destination,
        combiner,
        origins,
        reloader=lambda x: x,
        verbose=False,
        messager=None,
):
    """If any of the origin files have been updated since the
    destination was, run the combiner function on their contents and
    write its result to the destination, returning the result.

    The 'combiner' argument is a function taking a list of lists,
    typically, the result of reading multiple CSV files, and its
    result would typically be a list to be written to a CSV file.

    The 'origins' argument is a dictionary binding filename strings to
    row processing functions, so this function can be used to
    transform incoming data and merge it into a collection.  If a row
    processing function returns `None`, the row is skipped.

    Otherwise, read and return the destination file, applying the
    'reloader' argument to each entry in it, and keeping only the
    entries for which the 'reloader' returns a non-None value.

    The functions in the 'origins' dictionary, and the 'reloader'
    function, could typically be used to convert tabular data rows
    into Python objects.

    Reading and writing of files is done using the 'load' and 'save'
    functions from this package, which dispatch on the filename
    extensions.
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
            if file_newer_than_file(most_recently_modified(origins),
                                    destination)
            else [reload_entry
                  for reload_raw in load(destination,
                                         verbose=verbose,
                                         messager=messager)
                  if (reload_entry := reloader(reload_raw)) is not None])

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
