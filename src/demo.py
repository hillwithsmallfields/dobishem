#!/usr/bin/env python3

from dobishem import storage

TABLE_DICT = [
    {'species': 'felis catus', 'kingdom': 'animal', 'structure': 'quadruped'},
    {'species': 'amoeba proteus', 'kingdom': 'protist', 'structure': 'unicellular'},
    {'species': 'octopus vulgaris', 'kingdom': 'animal', 'structure': 'cephalopod'},
    {'species': 'pringlea antiscorbutica', 'kingdom': 'plant', 'structure': 'herbaceous'},
]

ORGANISMS_TABLE_FILE = "/tmp/organisms.csv"

storage.write_csv(ORGANISMS_TABLE_FILE, TABLE_DICT,
                  sort_columns=['kingdom'])
animals = storage.read_csv(ORGANISMS_TABLE_FILE,
                           result_type=dict,
                           key_column='species',
                           transform_row=lambda r: r if r['kingdom'] == 'animal' else None)
print(animals)
