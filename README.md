# FS25 Vehicle Condition Editor

A small Python utility for manually listing and updating vehicle condition values in a Farming Simulator 25 savegame `vehicles.xml` file.

The script can update:

- Vehicle age
- Operating time
- Dirt level
- Wetness level
- Wear level
- Damage level

It is intended for manual savegame maintenance, storytelling setup, or correcting vehicle condition values after moving equipment between saves, maps, or narrative series.

---

## Important

Always close Farming Simulator 25 before editing a savegame file.

The script creates a timestamped backup by default before writing changes, but you should still make a full savegame backup before using it.

Example save path:

```text
E:\My Games\FarmingSimulator2025\savegame9\vehicles.xml
````

---

## XML Values Edited

The script uses the normal FS25 savegame structure.

### Vehicle-level values

These are stored directly on the `<vehicle>` entry:

```xml
<vehicle age="12.000000" operatingTime="25.500000">
```

| Option             | XML attribute                   |
| ------------------ | ------------------------------- |
| `--age`            | `<vehicle age="...">`           |
| `--operating-time` | `<vehicle operatingTime="...">` |

### Dirt and wetness

These are stored under the vehicle’s `<washable>` section:

```xml
<washable>
    <dirtNode amount="0.250000" wetness="0.000000" />
</washable>
```

| Option      | XML attribute              |
| ----------- | -------------------------- |
| `--dirt`    | `<dirtNode amount="...">`  |
| `--wetness` | `<dirtNode wetness="...">` |

If a vehicle has multiple `<dirtNode>` entries, the script updates all of them.

### Wear and damage

These are stored under the vehicle’s `<wearable>` section:

```xml
<wearable damage="0.050000">
    <wearNode amount="0.150000" />
</wearable>
```

| Option     | XML attribute             |
| ---------- | ------------------------- |
| `--damage` | `<wearable damage="...">` |
| `--wear`   | `<wearNode amount="...">` |

If a vehicle has multiple `<wearNode>` entries, the script updates all of them.

---

## Requirements

Python 3.9 or newer is recommended.

The script only uses the Python standard library. No additional packages are required.

---

## Basic Usage

```powershell
python fs25_update_vehicle_condition.py "E:\My Games\FarmingSimulator2025\savegame9\vehicles.xml" --list
```

---

## Command Options

| Option                   | Description                                                                                                    |
| ------------------------ | -------------------------------------------------------------------------------------------------------------- |
| `vehicles_xml`           | Path to the savegame `vehicles.xml` file. Required.                                                            |
| `--list`                 | Lists matching vehicles and their current condition values. Does not modify the file.                          |
| `--age VALUE`            | Sets the vehicle age on the `<vehicle>` entry.                                                                 |
| `--operating-time VALUE` | Sets the vehicle operating time on the `<vehicle>` entry.                                                      |
| `--dirt VALUE`           | Sets all `<dirtNode amount>` values. Must be between `0.0` and `1.0`.                                          |
| `--wetness VALUE`        | Sets all `<dirtNode wetness>` values. Must be between `0.0` and `1.0`.                                         |
| `--wear VALUE`           | Sets all `<wearNode amount>` values. Must be between `0.0` and `1.0`.                                          |
| `--damage VALUE`         | Sets `<wearable damage>`. Must be between `0.0` and `1.0`.                                                     |
| `--match TEXT`           | Only lists or updates vehicles where the XML contains the matching text. Case-insensitive.                     |
| `--all`                  | Updates all matching vehicles. Required for update mode if `--match` is not used.                              |
| `--owned-only`           | Only lists or updates player-owned vehicles with `farmId="1"`.                                                 |
| `--create-missing`       | Creates missing `<washable>`, `<dirtNode>`, `<wearable>`, or `<wearNode>` sections when needed. Use carefully. |
| `--dry-run`              | Shows what would be changed without writing the file.                                                          |
| `--no-backup`            | Disables automatic timestamped backup creation. Not recommended.                                               |

---

## Listing Vehicles

List all vehicles in the save:

```powershell
python fs25_update_vehicle_condition.py "E:\My Games\FarmingSimulator2025\savegame9\vehicles.xml" --list
```

List only player-owned vehicles:

```powershell
python fs25_update_vehicle_condition.py "E:\My Games\FarmingSimulator2025\savegame9\vehicles.xml" --list --owned-only
```

`--owned-only` filters for:

```xml
farmId="1"
```

This avoids including map vehicles, traffic vehicles, and vehicles belonging to other farms.

List only vehicles matching a specific name, filename, mod name, or ID:

```powershell
python fs25_update_vehicle_condition.py "E:\My Games\FarmingSimulator2025\savegame9\vehicles.xml" --list --match johnDeere
```

Another example:

```powershell
python fs25_update_vehicle_condition.py "E:\My Games\FarmingSimulator2025\savegame9\vehicles.xml" --list --match mack
```

---

## Updating Vehicles

### Clean all player-owned vehicles

Dry run first:

```powershell
python fs25_update_vehicle_condition.py "E:\My Games\FarmingSimulator2025\savegame9\vehicles.xml" --all --owned-only --dirt 0 --wetness 0 --dry-run
```

Apply the change:

```powershell
python fs25_update_vehicle_condition.py "E:\My Games\FarmingSimulator2025\savegame9\vehicles.xml" --all --owned-only --dirt 0 --wetness 0
```

---

### Remove damage from all player-owned vehicles

```powershell
python fs25_update_vehicle_condition.py "E:\My Games\FarmingSimulator2025\savegame9\vehicles.xml" --all --owned-only --damage 0
```

---

### Reset dirt, wear, and damage on all player-owned vehicles

Dry run:

```powershell
python fs25_update_vehicle_condition.py "E:\My Games\FarmingSimulator2025\savegame9\vehicles.xml" --all --owned-only --dirt 0 --wetness 0 --wear 0 --damage 0 --dry-run
```

Apply:

```powershell
python fs25_update_vehicle_condition.py "E:\My Games\FarmingSimulator2025\savegame9\vehicles.xml" --all --owned-only --dirt 0 --wetness 0 --wear 0 --damage 0
```

---

### Update one vehicle by matching text

Example for a Mack truck:

```powershell
python fs25_update_vehicle_condition.py "E:\My Games\FarmingSimulator2025\savegame9\vehicles.xml" --match mack --age 480 --operating-time 620 --dirt 0.35 --wetness 0 --wear 0.45 --damage 0.08
```

Example for a John Deere:

```powershell
python fs25_update_vehicle_condition.py "E:\My Games\FarmingSimulator2025\savegame9\vehicles.xml" --match johnDeere --age 72 --operating-time 180 --dirt 0.20 --wear 0.18 --damage 0.02
```

---

## Suggested Value Ranges

### Dirt, wetness, wear, and damage

These values normally use a range from `0.0` to `1.0`.

|  Value | Meaning            |
| -----: | ------------------ |
|  `0.0` | None / clean / new |
|  `0.1` | Very light         |
| `0.25` | Noticeable         |
|  `0.5` | Heavy              |
| `0.75` | Severe             |
|  `1.0` | Maximum            |

### Example condition presets

| Narrative state      |   Age | Operating time |   Dirt |   Wear | Damage |
| -------------------- | ----: | -------------: | -----: | -----: | -----: |
| Brand new            |   `0` |            `0` | `0.00` | `0.00` | `0.00` |
| Lightly used         |  `12` |           `40` | `0.10` | `0.05` | `0.00` |
| Working farm machine |  `72` |          `250` | `0.25` | `0.20` | `0.03` |
| Older but maintained | `180` |          `600` | `0.35` | `0.40` | `0.08` |
| Tired ranch survivor | `360` |         `1200` | `0.55` | `0.65` | `0.20` |

---

## Dry Run Mode

Use `--dry-run` before making changes.

Example:

```powershell
python fs25_update_vehicle_condition.py "E:\My Games\FarmingSimulator2025\savegame9\vehicles.xml" --match mack --wear 0.45 --damage 0.08 --dry-run
```

This prints the changes that would be made but does not write the file.

---

## Backups

By default, the script creates a timestamped backup beside the original file before writing.

Example backup name:

```text
vehicles.xml.bak_20260504_153012
```

To disable this behaviour:

```powershell
python fs25_update_vehicle_condition.py "E:\My Games\FarmingSimulator2025\savegame9\vehicles.xml" --all --owned-only --dirt 0 --no-backup
```

Using `--no-backup` is not recommended unless you already have a separate save backup.

---

## Missing XML Sections

Some vehicles or modded objects may not have a `<washable>` or `<wearable>` section.

By default, the script does not create missing sections. It will skip those parts and report that they were not found.

To create missing sections, use:

```powershell
--create-missing
```

Example:

```powershell
python fs25_update_vehicle_condition.py "E:\My Games\FarmingSimulator2025\savegame9\vehicles.xml" --match mack --dirt 0.35 --wear 0.45 --damage 0.08 --create-missing
```

Use this carefully. It is generally safer to avoid adding condition sections to unusual objects, pallets, placeables, map vehicles, or traffic entries unless you know they should support those values.

---

## Recommended Workflow

1. Close Farming Simulator 25.
2. Back up the savegame folder.
3. List vehicles first:

```powershell
python fs25_update_vehicle_condition.py "E:\My Games\FarmingSimulator2025\savegame9\vehicles.xml" --list --owned-only
```

4. Run the intended update with `--dry-run`:

```powershell
python fs25_update_vehicle_condition.py "E:\My Games\FarmingSimulator2025\savegame9\vehicles.xml" --match mack --age 480 --operating-time 620 --dirt 0.35 --wear 0.45 --damage 0.08 --dry-run
```

5. If the output looks correct, run the same command without `--dry-run`.

6. Start the game and check the vehicle in the save.

---

## Notes

* `--owned-only` assumes the player farm is `farmId="1"`, which is normally correct for single-player saves.
* Multiplayer saves or unusual farm setups may use different farm IDs.
* `--match` is case-insensitive and searches vehicle attributes as well as child XML attributes.
* If a listed value shows as `mixed(N)`, the vehicle has multiple dirt or wear nodes with different values.
* If a listed value shows as `-`, that XML value was not found for that vehicle.

```
```

---

## Licence and Permissions

Copyright © 2026 SimGamerJen. All rights reserved.

You may download and use this software for personal use. You may not modify, redistribute, re-upload, or publish this software, in whole or in part, or any derivative version without prior written permission from SimGamerJen.
