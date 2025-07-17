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
