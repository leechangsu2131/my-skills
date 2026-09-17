#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

with open("ds_main_output.json", "r", encoding="utf-8") as f:
    data = json.load(f)

with open("combo_clean_list.txt", "w", encoding="utf-8") as f:
    combos = data.get("combos", {})
    for c_id, items in combos.items():
        f.write(f"=== {c_id} ===\n")
        for item in items:
            f.write(f"  {item['value']} : {item['label']}\n")
        f.write("\n")

print("Saved clean combo list to combo_clean_list.txt")
