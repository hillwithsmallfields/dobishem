import os

import dobishem.tabular_text

SAMPLE = """
    |--------+--------+-----------+-------------+-------+---------------------+--------------------------|
    | device | size   | part type | fstype      | flags | usage               | source of information    |
    |--------+--------+-----------+-------------+-------+---------------------+--------------------------|
    | sda1   | 999MB  | primary   | ext4        | boot  | /boot (main debian) | comment in fstab         |
    | sda2   | 4000MB | primary   |             |       | /mnt/other-os-a     | cfdisk                   |
    | sda3   | 4000MB | primary   | "linux"     |       | /mnt/other-os-b     | cfdisk                   |
    | sda4   | 1991GB | extended  |             |       |                     |                          |
    | sda5   | 16.0GB | logical   | ext4        | lvm   | / (main debian)     | comment in fstab         |
    | sda6   | 1975GB | logical   | lvm pv      |       | vg "original"       | lvm                      |
    | sdb1   | 999MB  | primary   | linux-swap  |       | swap                | parted, comment in fstab |
    | sdb2   | 4000MB | primary   | crypto-LUKS |       | /mnt/crypted        |                          |
    | sdb3   | 4000MB | primary   | linux-swap  |       |                     | fdisk                    |
    | sdb4   | 1991GB | extended  |             |       |                     |                          |
    | sdb5   | 16.0GB | logical   | ext4        |       | / (new devuan)      | fdisk                    |
    | sdb6   | 1975GB | logical   | lvm pv      | lvm   | vg "original"       | lvm                      |
    |--------+--------+-----------+-------------+-------+---------------------+--------------------------|
"""

SAMPLE_LINES=SAMPLE.split("\n")

def as_generator(things):
    return (thing for thing in things)

def test_read_tabular_dicts(tmp_path):
    read_in, columns = dobishem.tabular_text.read_tabular_to_dicts(as_generator(SAMPLE_LINES))
    assert len(list(read_in)) == 12

def test_write_tabular_dicts(tmp_path):
    data, original_cols = dobishem.tabular_text.read_tabular_to_dicts(as_generator(SAMPLE_LINES))
    data = list(data)
    filename = os.path.join(tmp_path, "roundtrip.table")
    with open(filename, 'w') as outstream:
        dobishem.tabular_text.write_tabular(outstream, data, ["device", "part type", "fstype", "size"])
    with open(filename) as backstream:
        back, cols_back = dobishem.tabular_text.read_tabular_to_dicts(backstream)
        back = list(back)
    print("original data", data)
    print("roundtripped data", back)
    for old, new in zip(data, back):
        if old != new:
            print("difference at", old, new)
            for key in set(old.keys()) | set(new.keys()):
                a = old.get(key, "")
                b = new.get(key, "")
                if a != b:
                    print("  ", key, a, b)
    with open(filename) as backstream:
        print("file")
        print(backstream.read())
    assert back == data
