#!/usr/bin/env python3
"""
FS25 vehicles.xml condition editor

Lists or updates:
- vehicle age
- vehicle operatingTime
- washable dirtNode amount
- washable dirtNode wetness
- wearable damage
- wearable wearNode amount

Designed for Farming Simulator 25 savegame vehicles.xml files.

Recommended:
1. Close the game.
2. Back up the save.
3. Run with --list or --dry-run first.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List or update vehicle age, operating time, dirt, wear, and damage in FS25 vehicles.xml."
    )

    parser.add_argument(
        "vehicles_xml",
        help="Path to savegame vehicles.xml",
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List matching vehicles and their current condition settings. Does not modify the file.",
    )

    parser.add_argument(
        "--age",
        type=float,
        default=None,
        help="Set <vehicle age>. Example: --age 12",
    )

    parser.add_argument(
        "--operating-time",
        type=float,
        default=None,
        help="Set <vehicle operatingTime>. Example: --operating-time 25.5",
    )

    parser.add_argument(
        "--dirt",
        type=float,
        default=None,
        help="Set all <dirtNode amount> values from 0.0 to 1.0. Example: --dirt 0.25",
    )

    parser.add_argument(
        "--wetness",
        type=float,
        default=None,
        help="Set all <dirtNode wetness> values from 0.0 to 1.0. Example: --wetness 0",
    )

    parser.add_argument(
        "--wear",
        type=float,
        default=None,
        help="Set all <wearNode amount> values from 0.0 to 1.0. Example: --wear 0.15",
    )

    parser.add_argument(
        "--damage",
        type=float,
        default=None,
        help="Set <wearable damage> from 0.0 to 1.0. Example: --damage 0.05",
    )

    parser.add_argument(
        "--match",
        default=None,
        help=(
            "Only list/update vehicles where filename, modName, uniqueId, type, "
            "configuration, or other attributes contain this text. Case-insensitive."
        ),
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Update all vehicles. Required for update mode if --match is not used.",
    )

    parser.add_argument(
        "--owned-only",
        action="store_true",
        help="Only list/update owned vehicles. Skips propertyState=NONE and farmId=0 vehicles.",
    )

    parser.add_argument(
        "--create-missing",
        action="store_true",
        help=(
            "Create missing <washable>, <dirtNode>, <wearable>, or <wearNode> sections "
            "when updating dirt/wear/damage. Use carefully."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without writing the file.",
    )

    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Do not create a timestamped backup before writing.",
    )

    return parser.parse_args()


def clamp_01(value: Optional[float], field_name: str) -> Optional[float]:
    if value is None:
        return None

    if value < 0.0 or value > 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0")

    return value


def format_number(value: float) -> str:
    return f"{value:.6f}"


def basename_from_filename(filename: str) -> str:
    if not filename:
        return ""

    clean = filename.replace("\\", "/")
    return clean.split("/")[-1]


def get_vehicle_display_name(vehicle: ET.Element) -> str:
    filename = vehicle.attrib.get("filename", "")
    base = basename_from_filename(filename)

    if base.lower().endswith(".xml"):
        base = base[:-4]

    mod_name = vehicle.attrib.get("modName", "")

    if mod_name:
        return f"{base} [{mod_name}]"

    return base or "<unknown>"


def vehicle_matches(
    vehicle: ET.Element,
    match_text: Optional[str],
    update_all: bool,
    owned_only: bool,
    list_mode: bool,
) -> bool:
    if owned_only:
        farm_id = vehicle.attrib.get("farmId", "")

        # In a normal single-player save, the player's farm is farmId="1".
        # This deliberately excludes map vehicles, traffic, and other farm-owned vehicles.
        if farm_id != "1":
            return False

    # In list mode, list everything unless --match is supplied.
    if list_mode and not match_text:
        return True

    if update_all:
        return True

    if not match_text:
        return False

    needle = match_text.lower()

    for value in vehicle.attrib.values():
        if needle in str(value).lower():
            return True

    for child in vehicle.iter():
        for value in child.attrib.values():
            if needle in str(value).lower():
                return True

    return False


def get_washable(vehicle: ET.Element, create_missing: bool = False) -> Optional[ET.Element]:
    washable = vehicle.find("washable")

    if washable is None and create_missing:
        washable = ET.SubElement(vehicle, "washable")

    return washable


def get_wearable(vehicle: ET.Element, create_missing: bool = False) -> Optional[ET.Element]:
    wearable = vehicle.find("wearable")

    if wearable is None and create_missing:
        wearable = ET.SubElement(vehicle, "wearable")

    return wearable


def get_dirt_nodes(vehicle: ET.Element, create_missing: bool = False) -> list[ET.Element]:
    washable = get_washable(vehicle, create_missing=create_missing)

    if washable is None:
        return []

    dirt_nodes = washable.findall("dirtNode")

    if not dirt_nodes and create_missing:
        dirt_node = ET.SubElement(washable, "dirtNode")
        dirt_node.set("amount", "0.000000")
        dirt_node.set("wetness", "0.000000")
        dirt_nodes = [dirt_node]

    return dirt_nodes


def get_wear_nodes(vehicle: ET.Element, create_missing: bool = False) -> list[ET.Element]:
    wearable = get_wearable(vehicle, create_missing=create_missing)

    if wearable is None:
        return []

    wear_nodes = wearable.findall("wearNode")

    if not wear_nodes and create_missing:
        wear_node = ET.SubElement(wearable, "wearNode")
        wear_node.set("amount", "0.000000")
        wear_nodes = [wear_node]

    return wear_nodes


def summarise_dirt(vehicle: ET.Element) -> str:
    dirt_nodes = get_dirt_nodes(vehicle)

    if not dirt_nodes:
        return "-"

    amounts = [node.attrib.get("amount", "-") for node in dirt_nodes]
    unique = sorted(set(amounts))

    if len(unique) == 1:
        return unique[0]

    return f"mixed({len(dirt_nodes)})"


def summarise_wetness(vehicle: ET.Element) -> str:
    dirt_nodes = get_dirt_nodes(vehicle)

    if not dirt_nodes:
        return "-"

    values = [node.attrib.get("wetness", "-") for node in dirt_nodes]
    unique = sorted(set(values))

    if len(unique) == 1:
        return unique[0]

    return f"mixed({len(dirt_nodes)})"


def summarise_wear(vehicle: ET.Element) -> str:
    wear_nodes = get_wear_nodes(vehicle)

    if not wear_nodes:
        return "-"

    values = [node.attrib.get("amount", "-") for node in wear_nodes]
    unique = sorted(set(values))

    if len(unique) == 1:
        return unique[0]

    return f"mixed({len(wear_nodes)})"


def summarise_damage(vehicle: ET.Element) -> str:
    wearable = get_wearable(vehicle)

    if wearable is None:
        return "-"

    return wearable.attrib.get("damage", "-")


def list_vehicles(vehicles: list[ET.Element], args: argparse.Namespace) -> None:
    rows: list[dict[str, str]] = []

    for index, vehicle in enumerate(vehicles, start=1):
        if not vehicle_matches(
            vehicle=vehicle,
            match_text=args.match,
            update_all=args.all,
            owned_only=args.owned_only,
            list_mode=True,
        ):
            continue

        rows.append(
            {
                "#": str(index),
                "Name": get_vehicle_display_name(vehicle),
                "Farm": vehicle.attrib.get("farmId", "-"),
                "State": vehicle.attrib.get("propertyState", "-"),
                "Age": vehicle.attrib.get("age", "-"),
                "OpTime": vehicle.attrib.get("operatingTime", "-"),
                "Dirt": summarise_dirt(vehicle),
                "Wet": summarise_wetness(vehicle),
                "Wear": summarise_wear(vehicle),
                "Damage": summarise_damage(vehicle),
                "UniqueId": vehicle.attrib.get("uniqueId", "-"),
            }
        )

    if not rows:
        print("No vehicles matched.")
        return

    headers = [
        "#",
        "Name",
        "Farm",
        "State",
        "Age",
        "OpTime",
        "Dirt",
        "Wet",
        "Wear",
        "Damage",
        "UniqueId",
    ]

    widths = {
        header: max(len(header), max(len(row[header]) for row in rows))
        for header in headers
    }

    print()
    print(f"Matched vehicles: {len(rows)}")
    print()

    header_line = "  ".join(header.ljust(widths[header]) for header in headers)
    print(header_line)
    print("-" * len(header_line))

    for row in rows:
        print("  ".join(row[header].ljust(widths[header]) for header in headers))

    print()
    print("Notes:")
    print("  - Age and OpTime are read from the <vehicle> header.")
    print("  - Dirt and Wet are read from <washable><dirtNode amount/wetness>.")
    print("  - Wear is read from <wearable><wearNode amount>.")
    print("  - Damage is read from <wearable damage>.")
    print("  - mixed(N) means the vehicle has multiple nodes with different values.")


def vehicle_label(vehicle: ET.Element) -> str:
    name = get_vehicle_display_name(vehicle)
    unique_id = vehicle.attrib.get("uniqueId", "")
    farm_id = vehicle.attrib.get("farmId", "")
    property_state = vehicle.attrib.get("propertyState", "")

    parts = [name]

    if farm_id:
        parts.append(f"farmId={farm_id}")

    if property_state:
        parts.append(f"state={property_state}")

    if unique_id:
        parts.append(f"uniqueId={unique_id}")

    return " | ".join(parts)


def set_vehicle_attr(vehicle: ET.Element, attr_name: str, new_value: str) -> Optional[str]:
    old_value = vehicle.attrib.get(attr_name)

    if old_value != new_value:
        vehicle.set(attr_name, new_value)
        return f"vehicle.{attr_name}: {old_value!r} -> {new_value!r}"

    return None


def update_vehicle(
    vehicle: ET.Element,
    age: Optional[float],
    operating_time: Optional[float],
    dirt: Optional[float],
    wetness: Optional[float],
    wear: Optional[float],
    damage: Optional[float],
    create_missing: bool,
) -> list[str]:
    changes: list[str] = []

    if age is not None:
        change = set_vehicle_attr(vehicle, "age", format_number(age))
        if change:
            changes.append(change)

    if operating_time is not None:
        change = set_vehicle_attr(vehicle, "operatingTime", format_number(operating_time))
        if change:
            changes.append(change)

    if dirt is not None or wetness is not None:
        dirt_nodes = get_dirt_nodes(vehicle, create_missing=create_missing)

        if not dirt_nodes:
            changes.append("washable.dirtNode: not found, skipped")
        else:
            for i, dirt_node in enumerate(dirt_nodes, start=1):
                if dirt is not None:
                    old_value = dirt_node.attrib.get("amount")
                    new_value = format_number(dirt)

                    if old_value != new_value:
                        dirt_node.set("amount", new_value)
                        changes.append(
                            f"washable.dirtNode[{i}].amount: {old_value!r} -> {new_value!r}"
                        )

                if wetness is not None:
                    old_value = dirt_node.attrib.get("wetness")
                    new_value = format_number(wetness)

                    if old_value != new_value:
                        dirt_node.set("wetness", new_value)
                        changes.append(
                            f"washable.dirtNode[{i}].wetness: {old_value!r} -> {new_value!r}"
                        )

    if damage is not None:
        wearable = get_wearable(vehicle, create_missing=create_missing)

        if wearable is None:
            changes.append("wearable.damage: not found, skipped")
        else:
            old_value = wearable.attrib.get("damage")
            new_value = format_number(damage)

            if old_value != new_value:
                wearable.set("damage", new_value)
                changes.append(f"wearable.damage: {old_value!r} -> {new_value!r}")

    if wear is not None:
        wear_nodes = get_wear_nodes(vehicle, create_missing=create_missing)

        if not wear_nodes:
            changes.append("wearable.wearNode: not found, skipped")
        else:
            for i, wear_node in enumerate(wear_nodes, start=1):
                old_value = wear_node.attrib.get("amount")
                new_value = format_number(wear)

                if old_value != new_value:
                    wear_node.set("amount", new_value)
                    changes.append(
                        f"wearable.wearNode[{i}].amount: {old_value!r} -> {new_value!r}"
                    )

    return changes


def indent_xml(tree: ET.ElementTree) -> None:
    ET.indent(tree, space="    ", level=0)


def main() -> int:
    args = parse_args()

    vehicles_path = Path(args.vehicles_xml).expanduser().resolve()

    if not vehicles_path.exists():
        print(f"ERROR: File not found: {vehicles_path}", file=sys.stderr)
        return 1

    if vehicles_path.name.lower() != "vehicles.xml":
        print(
            f"WARNING: Expected a file named vehicles.xml, got: {vehicles_path.name}",
            file=sys.stderr,
        )

    try:
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        tree = ET.parse(vehicles_path, parser=parser)
        root = tree.getroot()
    except ET.ParseError as exc:
        print(f"ERROR: Could not parse XML: {exc}", file=sys.stderr)
        return 1

    vehicles = root.findall(".//vehicle")

    if not vehicles:
        print("ERROR: No <vehicle> entries found.", file=sys.stderr)
        return 1

    if args.list:
        print(f"Loaded: {vehicles_path}")
        print(f"Found vehicles: {len(vehicles)}")
        list_vehicles(vehicles, args)
        return 0

    if not args.all and not args.match:
        print(
            "ERROR: Use either --all or --match TEXT so the script knows what to update.",
            file=sys.stderr,
        )
        return 1

    if (
        args.age is None
        and args.operating_time is None
        and args.dirt is None
        and args.wetness is None
        and args.wear is None
        and args.damage is None
    ):
        print(
            "ERROR: Nothing to update. Provide at least one of "
            "--age, --operating-time, --dirt, --wetness, --wear, --damage.",
            file=sys.stderr,
        )
        return 1

    if args.age is not None and args.age < 0:
        print("ERROR: --age cannot be negative.", file=sys.stderr)
        return 1

    if args.operating_time is not None and args.operating_time < 0:
        print("ERROR: --operating-time cannot be negative.", file=sys.stderr)
        return 1

    try:
        dirt = clamp_01(args.dirt, "--dirt")
        wetness = clamp_01(args.wetness, "--wetness")
        wear = clamp_01(args.wear, "--wear")
        damage = clamp_01(args.damage, "--damage")
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    matched_count = 0
    changed_count = 0

    print(f"Loaded: {vehicles_path}")
    print(f"Found vehicles: {len(vehicles)}")
    print()

    for vehicle in vehicles:
        if not vehicle_matches(
            vehicle=vehicle,
            match_text=args.match,
            update_all=args.all,
            owned_only=args.owned_only,
            list_mode=False,
        ):
            continue

        matched_count += 1

        before = copy.deepcopy(vehicle)

        changes = update_vehicle(
            vehicle=vehicle,
            age=args.age,
            operating_time=args.operating_time,
            dirt=dirt,
            wetness=wetness,
            wear=wear,
            damage=damage,
            create_missing=args.create_missing,
        )

        real_changes = [
            change for change in changes
            if "not found, skipped" not in change
        ]

        if real_changes:
            changed_count += 1
            print(f"UPDATE: {vehicle_label(before)}")
            for change in changes:
                print(f"  - {change}")
            print()
        else:
            print(f"NO CHANGE: {vehicle_label(vehicle)}")
            for change in changes:
                print(f"  - {change}")
            print()

    print(f"Matched vehicles: {matched_count}")
    print(f"Changed vehicles: {changed_count}")

    if matched_count == 0:
        print("No vehicles matched your filter. File was not changed.")
        return 0

    if args.dry_run:
        print("Dry run only. File was not written.")
        return 0

    if changed_count == 0:
        print("No actual changes made. File was not written.")
        return 0

    if not args.no_backup:
        timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = vehicles_path.with_suffix(f".xml.bak_{timestamp}")
        shutil.copy2(vehicles_path, backup_path)
        print(f"Backup created: {backup_path}")

    indent_xml(tree)
    tree.write(
        vehicles_path,
        encoding="utf-8",
        xml_declaration=True,
    )

    print(f"Updated file written: {vehicles_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())