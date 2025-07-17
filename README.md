dobishem
========

My utility code, written to be useful for more than one specific project.

The name is Albanian for "useful"; there are so many packages called
"utils", and I wrote the initial version of this code in Albania, so I
picked a local name to make it easier to spot among all the "utils".

Contains I/O and file-based caching for a start.

storage
-------

This provides:

* readers and writers for various formats, with particular
  attention to CSV, which it can arrange into lists, dictionaries and
  sets in ways that I have found useful.  Also, some dispatch functions
  for using the appropriate reader and writer functions according to the
  filenames.

* storage handlers which build filenames from templates

* functions for applying functions to files, including acting
  conditionally according to the relative filestamps (makefile style)

tabular_text
------------

Read and write org-mode files (see https://orgmode.org/)

data
----

Contains some support functions for tabular data.

nested_messages
---------------

Provides context handlers for indented messages, where each handler
adds another level of indentation, which disappears when the handler
exits.

dates
-----

Normalization of dates, and some functions for going back or forward
dates.  I'll probably remove this sometime, as
https://pypi.org/project/python-dateutil/ and
https://pypi.org/project/dateutils/ already handle these.