set -e
#
# Create the files the two tutorials register as assets, and print the digest
# the inference tutorial asks for.
#
# The download tutorial needs one file to hand out. The inference tutorial needs
# three: two cohorts, held by two different hospitals, that stay behind their own
# guardians, and the script that travels to both of them. The script's digest is
# what each owner's policy approves and what every FL client re-measures at
# redemption time, so it is printed here rather than left for the reader to
# derive.
#
# The two cohorts are deliberately different sizes. A federated round reports one
# aggregate weighted by how much data each site ran over, and two identical files
# would hide whether that weighting is real.
#
# Safe to re-run: it overwrites every file with the same content, so the digest
# does not move.

DATA_FILE=/tmp/asset_data.txt
COHORT_A_FILE=/tmp/hospital_a_cohort.csv
COHORT_B_FILE=/tmp/hospital_b_cohort.csv
SCRIPT_FILE=/tmp/inference_script.py

# ---- the download tutorial's dataset -------------------------------------
echo "The eagle lands at midnight." > "$DATA_FILE"

# ---- the inference tutorial's first cohort -------------------------------
# Never leaves its guardian's host; only the metrics computed over it come back.
cat > "$COHORT_A_FILE" <<'EOF'
patient_id,age,sex,hba1c,bmi,diagnosis
A001,54,F,7.8,31.2,type-2-diabetes
A002,61,M,6.4,27.9,prediabetes
A003,47,F,9.1,34.6,type-2-diabetes
A004,58,M,5.6,24.1,control
A005,66,F,8.3,29.8,type-2-diabetes
A006,52,M,6.9,30.4,prediabetes
A007,45,F,5.2,22.7,control
A008,70,M,8.8,33.1,type-2-diabetes
EOF

# ---- the inference tutorial's second cohort ------------------------------
# A different hospital's patients: same columns, more rows, and never pooled with
# the first. The whole point of the round is that these two files are summarized
# together without either leaving the building it is in.
cat > "$COHORT_B_FILE" <<'EOF'
patient_id,age,sex,hba1c,bmi,diagnosis
B001,49,F,8.9,32.7,type-2-diabetes
B002,63,M,7.2,28.4,type-2-diabetes
B003,55,F,5.9,25.3,control
B004,71,M,9.4,35.9,type-2-diabetes
B005,42,F,6.1,26.8,prediabetes
B006,67,M,8.1,31.5,type-2-diabetes
B007,38,F,5.4,23.2,control
B008,59,M,7.6,30.1,type-2-diabetes
B009,64,F,6.7,29.0,prediabetes
B010,51,M,9.9,36.4,type-2-diabetes
B011,46,F,5.8,24.9,control
B012,69,M,8.5,33.8,type-2-diabetes
EOF

# ---- the inference tutorial's script -------------------------------------
# What every FL client in the round would run against its own cohort. It is
# registered as its own asset behind a public guardian, so the digest below is
# over exactly the bytes any party can fetch and check for themselves.
cat > "$SCRIPT_FILE" <<'EOF'
"""Cohort summary for a type-2 diabetes study.

Runs where the data is. Reads the cohort the guardian released to the FL client
on this host and reports aggregate metrics -- never rows. Every site in a
federated round runs this same file over its own patients, and only what it
returns here is ever combined.
"""

import csv
import sys


def summarize(rows):
    cases = [r for r in rows if r["diagnosis"] == "type-2-diabetes"]
    hba1c = [float(r["hba1c"]) for r in cases]
    return {
        "cohort_size": len(rows),
        "cases": len(cases),
        "mean_hba1c_in_cases": round(sum(hba1c) / len(hba1c), 2) if hba1c else None,
    }


def main():
    rows = list(csv.DictReader(sys.stdin))
    for name, value in summarize(rows).items():
        print(f"{name}={value}")


if __name__ == "__main__":
    main()
EOF

DIGEST="sha256:$(sha256sum "$SCRIPT_FILE" | awk '{print $1}')"

cat <<EOF
Tutorial files written.

  download tutorial  dataset : $DATA_FILE
  inference cohort, hospital A: $COHORT_A_FILE ($(wc -c < "$COHORT_A_FILE") bytes)
  inference cohort, hospital B: $COHORT_B_FILE ($(wc -c < "$COHORT_B_FILE") bytes)
  inference tutorial script  : $SCRIPT_FILE

The inference tutorial asks for the script's digest. It is:

  $DIGEST
EOF
