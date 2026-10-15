#!/usr/bin/env python3
"""Create EXP-043 provenance manifest and rebuild canonical experiment index."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.lpf.experiment_manifest import new_manifest, experiment_index, validate_manifest
from src.lpf.constraint_versions import ROOT

def main():
    root=Path(ROOT)
    directory=root/"experiments/chatgpt_topology_search/runs/EXP-043"
    directory.mkdir(parents=True,exist_ok=True)
    dest=directory/"manifest.json"
    if dest.exists():
        print("EXP-043 manifest exists; do not overwrite provenance")
        return
    purpose=("RF-T005 EXP-021 C-H30p0002 corrected parallel bridge; "
             "area/IL Pareto study including GJM deletion and PCB substitution")
    scope={
        "experiment_id":"EXP-043",
        "objective":"full_lpf",
        "constraint_id":"RF-T005",
        "phase":"Phase 2",
        "source":"User request: 3-L topology with a single shunt L and controlled multiple resonance modes",
        "baseline":"EXP-042 corrected parallel Cf2/Cv2 RF-T005 chip-area Pareto",
        "allowed_3L_branches":"two series inductors and one tapped shunt inductor",
        "chip_area_search": [3.0, 11/3, 13/3],
        "interim_worst_IL_target_db":0.8,
        "formal_worst_IL_target_db":0.3,
        "minimum_harmonic_db":30.0,
        "nominal_harmonic_db":35.0,
        "objective":"minimax 6-setting full-band IL with strict H2/H3, compare Pareto",
        "candidate_selection":"retain best per topology, numerical counterexamples, independent MNA of finalists",
    }
    manifest=new_manifest("EXP-043",purpose,scope,objective="full_lpf",
                          seed=20261016,root=root,constraint_id="RF-T005",allow_trial=True)
    manifest["execution"]["status"]="planned"
    manifest["validation"]["numerical"]="not_run"
    manifest["validation"]["independent"]="not_run"
    manifest["validation"]["implementation"]="not_run"
    manifest["validation"]["analysis_grid"]="not_run_before_solver"
    manifest["validation"]["independent_grid"]="not_run_before_solver"
    manifest["limitations"] += [
       "New topology search not yet executed at manifest creation.",
       "Finite local search cannot establish global feasibility/non-feasibility.",
       "0.8 dB interim target is not a modification of approved formal RF-F003.",
       "Q(f), SRF, EM, source S2P reference planes, PCB and variable-C implementation remain unverified."
    ]
    validate_manifest(manifest,root=root)
    dest.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
    all_manifests=[]
    for p in sorted((root/"experiments/chatgpt_topology_search/runs").glob("EXP-*/manifest.json")):
        all_manifests.append((p.relative_to(root).as_posix(),
                              json.loads(p.read_text(encoding="utf-8"))))
    index=experiment_index(all_manifests)
    (root/"data/experiment_index.csv").write_text(index,encoding="utf-8")
    inventory=root/"data/experiment_evidence_inventory.csv"
    with inventory.open(newline="",encoding="utf-8") as h:
        original=h.read()
    if "EXP-043," not in original:
        row="EXP-043,trial,RF-T005,full_lpf,planned,not_run,not_run,not_run,0,true,true,true,false,none,experiments/chatgpt_topology_search/runs/EXP-043/manifest.json"
        inventory.write_text(original.rstrip()+"\n"+row+"\n",encoding="utf-8")
    print("Created",dest,"and updated index; number of manifests",len(all_manifests))

if __name__=="__main__":
    main()
