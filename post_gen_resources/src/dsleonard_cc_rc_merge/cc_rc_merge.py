#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#     "pyyaml",
#     "qx",
# ]
#
# [tool.uv.sources]
# qx = { git = "https://github.com/DSLeonard-coding/qx.git" }
# ///
# cookiecutter rc_maker D. S. Leonard 2026
# Merges present settings with cookiecutterrc minus excludes.

import json
import os
import yaml
from dsleonard_qx import *

def merge_rc_from_json(json_path, rc_path=".cookiecutterrc"):
    msg(f"\nMerging cookiecutter fields to your editable {rc_path}")
    try:
        existing_data = {}
        if os.path.exists(rc_path):
            with open(rc_path, 'r') as f:
                # If the file is garbled/empty, safe_load returns None, so we fallback to {}
                existing_data = yaml.safe_load(f) or {}

        # Ensure it's a dict and has 'default_context'
        if not isinstance(existing_data, dict):
            existing_data = {}

        if "default_context" not in existing_data:
            existing_data["default_context"] = {}
            msg(f"🛠️  Initialised missing 'default_context' in {rc_path}")

        rc_context = existing_data["default_context"]

        if isinstance(json_path, dict):
            template_data = json_path
            blacklist = template_data.get("_exclude_from_rc", [])
            for key in list(template_data.keys()):
                if key in blacklist or key.startswith('_'):
                    template_data.pop(key, None)

        else:
            with open(json_path, 'r') as f:
                template_data = json.load(f)

        # Merge only missing fields
        added_fields = []
        for key, value in template_data.items():
            if key.startswith('_') or (isinstance(value, str) and "{"+"{" in value):
                continue

            # If the key isn't there, add it
            if key not in rc_context:
                rc_context[key] = value
                added_fields.append(key)
            else:
                msg(f"Skipping key {key} already in your {rc_path}")


        # Save back the whole structure
        if added_fields:
            with open(rc_path, 'w') as f:
                yaml.dump(existing_data, f, default_flow_style=False, sort_keys=False)
            msg(f"✅ Merged {len(added_fields)} new fields into {rc_path}")
        else:
            msg(f"ℹ️ {rc_path} is already up to date.")

    except Exception as e:
        print(f"⚠️ Error: {e}")


if __name__ == "__main__":
    generate_rc_from_json('.cookiecutter.json')
