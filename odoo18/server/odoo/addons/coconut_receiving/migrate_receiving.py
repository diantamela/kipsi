# -*- coding: utf-8 -*-
"""
Migration Script: coconut_receiving 18.0.3.0.0
=================================================
Purpose: Migrate existing coconut.receipt records that use legacy net_weight field
to the new weighbridge structure (gross_vehicle_weight, tare_vehicle_weight, net_received_weight).

Existing records were created with:
  net_weight = direct entry (not computed)
  gross_weight = net_weight + total_reject  (computed, stored)

New structure:
  gross_vehicle_weight = bruto kendaraan (UNKNOWN from old data)
  tare_vehicle_weight  = tara kendaraan (UNKNOWN from old data)
  net_received_weight  = computed = gross - tare - pot

MIGRATION STRATEGY:
  Since we don't have the original gross/tare breakdown, we approximate:
  - Set gross_vehicle_weight = net_weight (legacy) + tare_vehicle_weight
  - Set tare_vehicle_weight = 0  (conservative default)
  - This makes net_received_weight = net_weight (legacy)

  For records where gross_weight (legacy computed) is available and > net_weight:
  - Set gross_vehicle_weight = gross_weight (which was net + total_reject)
  - Set tare_vehicle_weight = gross_weight - net_weight
  - This approximation: gross = net + reject, tare = reject (incorrect but preserves net)

RECOMMENDED: Use net_weight directly as gross_vehicle_weight, tare=0, pot=0.
This preserves the stock move history while making the weighbridge form consistent.

HOW TO RUN:
  python odoo-bin shell -c odoo.conf -d <database_name>
  Then paste and execute the script content, OR:
  python odoo-bin shell -c odoo.conf -d <database_name> < migrate_receiving.py

SAFE: This script only updates records where gross_vehicle_weight = 0
      (i.e., not yet migrated). It will NOT overwrite manually entered data.
"""

import logging
_logger = logging.getLogger(__name__)


def migrate_coconut_receipts(env):
    """
    Migrate legacy net_weight → new weighbridge fields.
    Only updates records where gross_vehicle_weight = 0 (unmigrated).
    """
    receipts = env['coconut.receipt'].search([
        ('gross_vehicle_weight', '=', 0.0),
    ])
    _logger.info("Found %d unmigrated coconut.receipt records.", len(receipts))

    migrated = 0
    skipped = 0
    for rec in receipts:
        legacy_net = rec.net_weight  # old field
        if legacy_net <= 0:
            _logger.warning(
                "Receipt %s has net_weight=0 – skipping migration.", rec.name
            )
            skipped += 1
            continue

        try:
            # Set gross = legacy_net (so net_received_weight will = legacy_net)
            # tare = 0, pot = 0
            rec.write({
                'gross_vehicle_weight': legacy_net,
                'tare_vehicle_weight': 0.0,
                'pot_weight': 0.0,
            })
            migrated += 1
            _logger.info(
                "Migrated receipt %s: net_weight=%s → gross_vehicle_weight=%s",
                rec.name, legacy_net, legacy_net,
            )
        except Exception as e:
            _logger.error("Failed to migrate receipt %s: %s", rec.name, e)
            skipped += 1

    _logger.info(
        "Migration complete: %d migrated, %d skipped.", migrated, skipped
    )
    return migrated, skipped


# ── When running via odoo-bin shell ──
if __name__ == '__main__':
    # 'env' is defined globally when executing inside `odoo-bin shell`.
    # We reference it dynamically to satisfy static linters.
    current_env = globals().get('env')
    if current_env:
        result = migrate_coconut_receipts(current_env)
        print(f"Migrated: {result[0]}, Skipped: {result[1]}")
        current_env.cr.commit()
        print("Committed to database.")
    else:
        print("Error: This script must be executed within 'odoo-bin shell' environment.")
