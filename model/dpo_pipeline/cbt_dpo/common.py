"""외부 데이터 경로에 의존하지 않는 공통 검증·직렬화."""
import hashlib
import json
from pathlib import Path

STRING={'type':'string'}
INTEGER={'type':'integer'}
DECISION={'type':'string','enum':['appropriate','needs_improvement','insufficient_context']}

def object_schema(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    temporary.replace(path)

def numbered_turns(turns):
    return [dict(turn_id=index,**turn) for index,turn in enumerate(turns,1)]

def check_quote(quote,source):
    if not isinstance(quote,str) or not quote.strip() or quote not in source:
        raise ValueError('근거 인용이 실제 입력의 부분 문자열이 아닙니다.')

from . import backend as codex_roles
