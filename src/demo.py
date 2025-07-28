#!/usr/bin/env python3

import tempfile

from dobishem import storage

###############################
# Directories as dictionaries #
###############################

etc = storage.DirectoryAsDictionary("/etc")

print("There are", len(etc), "entries in /etc")
print(list(etc.keys()))
print("The contents of /etc/crontab:", etc["crontab"])
print("The contents of /etc/X11", etc["X11"])
print("Whether /etc contains passwd:", "passwd" in etc)

with tempfile.TemporaryDirectory() as tempdirname:
    tempdir = storage.DirectoryAsDictionary(tempdirname, writable=True)
    for name in ['crontab', 'group', 'hosts', 'motd', 'passwd', 'resolv.conf']:
        tempdir[name] = etc[name]
    print("The temporary directory is", tempdirname, "and it contains", len(tempdir), "entries")
    print("The entry names are", tempdir.keys())

    for kv in tempdir.items():
        print("kv is", kv)
        # for a in kv:
        #     print(" got", a, "from kv")
        # k, v = kv
        # print("k is", k, "and v is", v)

    for k, v in tempdir.items():
        print("----------------")
        print(k)
        print("================")
        print(v)
        break
    print("----------------")

################
# Tabular data #
################

TABLE_DICT = [
    {'species': 'felis catus', 'kingdom': 'animal', 'structure': 'quadruped'},
    {'species': 'amoeba proteus', 'kingdom': 'protist', 'structure': 'unicellular'},
    {'species': 'octopus vulgaris', 'kingdom': 'animal', 'structure': 'cephalopod'},
    {'species': 'pringlea antiscorbutica', 'kingdom': 'plant', 'structure': 'herbaceous'},
    {'species': 'loxodonta africana', 'kingdom': 'animal', 'structure': 'quadruped'},
    {'species': 'muntiacus reevesi', 'kingdom': 'animal', 'structure': 'quadruped'},
    {'species': 'arabidopsis thaliana', 'kingdom': 'plant', 'structure': 'herbaceous'},
    {'species': 'quercus robur', 'kingdom': 'plant', 'structure': 'woody'},
]

ORGANISMS_TABLE_FILE = "/tmp/organisms.csv"

storage.write_csv(ORGANISMS_TABLE_FILE, TABLE_DICT,
                  sort_columns=['kingdom'])

animals_table = storage.read_csv(ORGANISMS_TABLE_FILE,
                                 result_type=dict,
                                 key_column='species',
                                 transform_row=lambda r: r if r['kingdom'] == 'animal' else None)
print("The animals, as a table:", animals_table)
for k, v in animals_table.items():
    print("  ", k, v)

animals_set = storage.read_csv(ORGANISMS_TABLE_FILE,
                               result_type=set,
                               key_column='kingdom')
print("The organisms, grouped by kingdom:", animals_set)
for k, v in animals_set.items():
    print("  ", k, ":", ", ".join(e['species'] for e in v))
