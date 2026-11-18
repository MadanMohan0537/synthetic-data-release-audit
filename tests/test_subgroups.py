import unittest

from synthseal.fixtures import adults
from synthseal.studio import generate, model_accuracy, subgroup_utility_report


class SubgroupUtilityTests(unittest.TestCase):
    def setUp(self):
        data=adults(); self.train=data[:179]+[data[-1]]; self.test=data[179:239]
        self.synth=generate(self.train,180)

    def test_report_reconciles_holdout_denominators(self):
        report=subgroup_utility_report(self.train,self.test,self.synth)
        self.assertEqual(len(self.test),sum(row["test_cases"] for row in report["subgroups"]))
        self.assertEqual(3,report["eligible_subgroups"])

    def test_intervals_are_deterministic(self):
        self.assertEqual(subgroup_utility_report(self.train,self.test,self.synth),subgroup_utility_report(self.train,self.test,self.synth))

    def test_seeded_subgroup_collapse_is_blocked(self):
        collapsed=[dict(row,target=0) if row["region"]=="South" else dict(row) for row in self.synth]
        report=subgroup_utility_report(self.train,self.test,collapsed)
        self.assertFalse(report["release_gate_passed"])
        self.assertEqual(["South"],report["flagged_subgroups"])
        south=next(row for row in report["subgroups"] if row["group"]=="South")
        self.assertEqual("missing_training_label",south["status"])

    def test_collapse_can_hide_inside_acceptable_overall_gap(self):
        collapsed=[dict(row,target=0) if row["region"]=="South" else dict(row) for row in self.synth]
        gap=model_accuracy(self.train,self.test)-model_accuracy(collapsed,self.test)
        self.assertLess(abs(gap),.25)
        self.assertFalse(subgroup_utility_report(self.train,self.test,collapsed)["release_gate_passed"])

    def test_sparse_group_is_visible_but_not_flagged(self):
        tiny=self.test[:5]
        report=subgroup_utility_report(self.train,tiny,self.synth,minimum_test_cases=10)
        self.assertTrue(all(not row["risk_flag"] for row in report["subgroups"]))
        self.assertTrue(all(row["status"]=="insufficient_holdout" for row in report["subgroups"]))

    def test_invalid_dimension_rejected(self):
        with self.assertRaises(ValueError): subgroup_utility_report(self.train,self.test,self.synth,dimension="age")

    def test_invalid_parameters_rejected(self):
        with self.assertRaises(ValueError): subgroup_utility_report(self.train,self.test,self.synth,minimum_test_cases=0)
        with self.assertRaises(ValueError): subgroup_utility_report(self.train,self.test,self.synth,draws=99)

    def test_regular_release_reports_uncertainty(self):
        report=subgroup_utility_report(self.train,self.test,self.synth)
        evaluated=[row for row in report["subgroups"] if row["status"]=="evaluated"]
        self.assertTrue(evaluated)
        self.assertTrue(all(len(row["accuracy_drop_ci"])==2 for row in evaluated))


if __name__=="__main__": unittest.main()
