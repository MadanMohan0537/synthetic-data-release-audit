import argparse,csv,json
from pathlib import Path
from .fixtures import adults
from .studio import evaluate_release,generate,model_accuracy,rare_disclosure_audit,remove_exposed,subgroup_utility_report

def main()->None:
    p=argparse.ArgumentParser(); p.add_argument("--output",type=Path,default=Path("release")); args=p.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    data=adults(); train=data[:179]+[data[-1]]; test=data[179:239]
    base=generate(train,180); challenged=base+[dict(train[-1])]
    before=evaluate_release(train,test,challenged); findings=rare_disclosure_audit(train,challenged)
    cleaned=remove_exposed(challenged,findings); after=evaluate_release(train,test,cleaned)
    collapsed=[dict(row,target=0) if row["region"]=="South" else dict(row) for row in cleaned]
    collapse_audit=subgroup_utility_report(train,test,collapsed)
    collapse_overall_gap=model_accuracy(train,test)-model_accuracy(collapsed,test)
    with (args.output/"synthetic.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(cleaned[0])); w.writeheader(); w.writerows(cleaned)
    report={"product":"SynthSeal","before_remediation":before,"after_remediation":after,
      "subgroup_utility_experiment":{"seeded_group":"South","overall_utility_gap":collapse_overall_gap,
        "overall_within_budget":abs(collapse_overall_gap)<.25,"audit":collapse_audit,
        "acceptance_passed":abs(collapse_overall_gap)<.25 and not collapse_audit["release_gate_passed"] and collapse_audit["flagged_subgroups"]==["South"]}}
    (args.output/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    card=f"""# SynthSeal data card

- Source: deterministic Adult-shaped synthetic fixture; no real people.
- Purpose: demonstrate utility/privacy release evidence.
- Rows released: {len(cleaned)}
- TSTR utility gap: {after['utility_gap']:.3f}
- Membership attack rate: {after['membership_attack_rate']:.3f}
- Rare-record exposures: {before['rare_exposures']} before, {after['rare_exposures']} after remediation.
- Attack flags: {before['attack_ensemble']['risk_flags']} before, {after['attack_ensemble']['risk_flags']} after remediation.
- Release recommendation: {after['attack_ensemble']['release_recommendation']}.
- Subgroup utility gate: {'pass' if after['subgroup_utility']['release_gate_passed'] else 'block'}; eligible groups: {after['subgroup_utility']['eligible_subgroups']}.
- Not approved for decisions about people or as evidence of formal privacy.
"""
    (args.output/"DATA_CARD.md").write_text(card)
    print(json.dumps({"released_rows":len(cleaned),"rare_exposures_before":before["rare_exposures"],"rare_exposures_after":after["rare_exposures"],"attack_flags_after":after["attack_ensemble"]["risk_flags"],"utility_gap_after":after["utility_gap"],"subgroup_gate_after":after["subgroup_utility"]["release_gate_passed"],"seeded_subgroup_collapse_detected":report["subgroup_utility_experiment"]["acceptance_passed"]},indent=2))
if __name__=="__main__": main()

