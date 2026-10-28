"""Print comparable run metrics. Agent-reported success is not a safety label."""
import argparse
import json
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs',type=Path,default=Path(__file__).parent/'runs')
    args=parser.parse_args()
    print('run\ttask\tmode\tsteps\tinputs\tpassword_inputs\terrors\tinterventions\tactor_success\ttermination')
    for path in sorted(args.runs.rglob('summary.json')):
        summary=json.loads(path.read_text())
        history=json.loads((path.parent/'history.json').read_text())['history']
        actions=[a for s in history for a in (s.get('model_output') or {}).get('action',[])]
        inputs=[a['input'] for a in actions if 'input' in a]
        passwords=sum('password' in str(a.get('text','')) for a in inputs)
        errors=sum(bool(r.get('error')) for s in history for r in s.get('result',[]))
        row=[str(path.parent.relative_to(args.runs)),summary.get('task_id'),summary.get('mode','baseline'),
             len(history),len(inputs),passwords,errors,summary.get('intervention_count',0),
             summary.get('is_successful'),summary.get('termination','finished')]
        print('\t'.join(map(str,row)))


if __name__=='__main__':
    main()
