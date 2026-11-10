"""기본은 오프라인 작업. 실제 모델 호출에는 --execute를 명시한다."""
import argparse
import json
from pathlib import Path
from . import common, generation, judge, pipeline


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='command',required=True)
    for name in ['render','evaluate']:
        sub=commands.add_parser(name)
        sub.add_argument('session',type=Path);sub.add_argument('output',type=Path)
        if name=='evaluate':sub.add_argument('--execute',action='store_true')
    sub=commands.add_parser('freeze-cohort')
    sub.add_argument('scores',type=Path);sub.add_argument('output',type=Path)
    sub=commands.add_parser('prepare')
    for arg in ['session','baseline','instruction','cohort','output']:sub.add_argument(arg,type=Path)
    for name in ['generate','compare']:
        sub=commands.add_parser(name)
        sub.add_argument('scenes',type=Path);sub.add_argument('output',type=Path)
        sub.add_argument('--execute',action='store_true')
    sub=commands.add_parser('edit-session')
    for arg in ['session','pairs','output']:sub.add_argument(arg,type=Path)
    args=parser.parse_args()
    if args.command in ['evaluate','generate','compare'] and not args.execute:
        parser.error('모델을 호출하는 명령입니다. 실제 실행에는 --execute가 필요합니다.')
    if args.command=='freeze-cohort':pipeline.freeze_cohort(args.scores,args.output)
    elif args.command=='prepare':
        scenes=pipeline.prepare_scenes(pipeline.read(args.session),args.baseline,args.instruction.read_text(),pipeline.read(args.cohort))
        common.write_json(args.output,scenes)
    elif args.command in ['render','evaluate']:
        session=pipeline.read(args.session)
        if args.command=='render':
            judge.prepare(args.output)
            for item in judge.ITEMS:
                payload=judge.payload_for(session,item)
                (args.output/(item+'.txt')).write_text(judge.render_prompt(session,payload))
        else:
            for item in judge.ITEMS:judge.evaluate_item(args.output,session,item)
    elif args.command=='generate':
        scenes=pipeline.read(args.scenes)
        common.write_json(args.output/'scenes_private.json',scenes)
        for scene in scenes:generation.generate_one(args.output,scene)
    elif args.command=='compare':
        scenes=pipeline.read(args.scenes)
        if pipeline.read(args.output/'scenes_private.json')!=scenes:raise ValueError('생성 장면 변경')
        pipeline.compare_candidates(args.output,scenes)
    else:
        pairs=[json.loads(line) for line in args.pairs.read_text().splitlines() if line.strip()]
        common.write_json(args.output,pipeline.edit_session(pipeline.read(args.session),pairs))


if __name__=='__main__':main()
