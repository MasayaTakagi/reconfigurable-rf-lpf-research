"""Vectorized Phase2 target-0.40dB engine agrees with independently verified A7-01."""
import importlib.util
import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"experiments/chatgpt_topology_search/runs/EXP-004/sweep_040.py"
spec=importlib.util.spec_from_file_location("exp004_vector_solver",SOURCE)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Target040EngineTests(unittest.TestCase):
    def test_reference_and_enumeration(self):
        self.assertEqual(len(module.jobs()),140)
        d=json.loads(module.REF.read_text(encoding="utf-8"))
        module.reference_check(d)

    def test_cost_and_tuning_node_conventions(self):
        names={x["family"] for x in module.jobs()}
        self.assertEqual(names,{"three_series_two_ground_controls",
                                "two_series_two_shunt","five_chip_three_GJM"})
        for x in module.jobs():
            self.assertEqual(len(x["order"]),x["Lcount"])
            self.assertEqual(len(x["Cedges"]),(4 if x["Lcount"]==4 else 3))
            self.assertEqual(len(set(x["order"])),x["Lcount"])
            self.assertTrue(all(a in (-1,0,1,2,3,4) and b in (-1,0,1,2,3,4)
                                for a,b in x["Ledges"]+x["Cedges"]))


if __name__=="__main__":
    unittest.main()
