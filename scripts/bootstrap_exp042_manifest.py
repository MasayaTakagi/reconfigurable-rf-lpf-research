#!/usr/bin/env python3
"""Create EXP-042 provenance manifest and rebuild canonical experiment index."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.lpf.experiment_manifest import new_manifest, experiment_index, validate_manifest
from src.lpf.constraint_versions import ROOT

def main():
    root=Path(ROOT)
    directory=root/"experiments/chatgpt_topology_search/runs/EXP-042"
    dest=directory/"manifest.json"
    if dest.exists():
        print("EXP-042 manifest exists; do not overwrite provenance")
        return
    purpose=("RF-T005 EXP-021 C-H30p0002 corrected parallel bridge; "
             "area/IL Pareto study including GJM deletion and PCB substitution")
    scope={
        "experiment_id":"EXP-042",
        "objective":"full_lpf",
        "constraint_id":"RF-T005",
        "phase":"Phase 2",
        "source":"EXP-021 C-H30p0002 figure; Cf2||Cv2",
        "variants":["original","cf1","cf2","both","pcb_cf1","pcb_cf2","pcb_both"],
        "chip_area_units":[6,5.333333333333333,4.666666666666667],
        "interim_worst_IL_target_db":0.8,
        "formal_worst_IL_target_db":0.3,
        "minimum_harmonic_db":30.0,
        "nominal_harmonic_db":35.0,
        "source_run_ids":[38773925329,38774957692,38775347911,38775558755,38775559008],
        "original_archived_evidence":"preliminary_js_5pt.json, dense_1001_independent_check.json",
    }
    manifest=new_manifest("EXP-042",purpose,scope,objective="full_lpf",
                          seed=20261016,root=root,constraint_id="RF-T005",allow_trial=True)
    manifest["execution"]["status"]="partial"
    manifest["validation"]["numerical"]="screened"
    manifest["validation"]["independent"]="passed"
    manifest["validation"]["implementation"]="not_run"
    manifest["validation"]["analysis_grid"]="28 separate bands x 1001 points; finite only"
    manifest["validation"]["independent_grid"]="84 explicit 9x9 branch MNA checks per chosen candidate"
    manifest["limitations"] += [
       "Ongoing Phase 2 local exploration; no mathematical global optimum.",
       "Formal RF-F003 remains unchanged: interim 0.8dB target is EXP-042-only.",
       "New 30-dB and 35-dB SLSQP baseline runs and multiple area variants are local best-found.",
       "Not every run/artifact has yet been curated as a permanent Git checkpoint.",
       "SRF, frequency-dependent Q, EM, tolerance, simultaneous k implementation unverified.",
    ]
    validate_manifest(manifest,root=root)
    dest.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
    all_manifests=[]
    for p in sorted((root/"experiments/chatgpt_topology_search/runs").glob("EXP-*/manifest.json")):
        all_manifests.append((p.relative_to(root).as_posix(),
                              json.loads(p.read_text(encoding="utf-8"))))
    index=experiment_index(all_manifests)
    (root/"data/experiment_index.csv").write_text(index,encoding="utf-8")
    print("Created",dest,"and updated index; number of manifests",len(all_manifests))

if __name__=="__main__":
    main()
