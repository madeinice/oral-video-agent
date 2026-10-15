"""Conservative RunningHub AI-app client. Submit is a dry run unless --execute."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

SECRET_FIELDS={"apikey","api_key","authorization","password","secret","curl","netwssurl"}
ALLOWED_BASES={"https://www.runninghub.cn","https://runninghub.cn","https://www.runninghub.ai","https://runninghub.ai"}


def safe(value):
    key=os.getenv("RUNNINGHUB_API_KEY")
    if isinstance(value,str): return value.replace(key,"[REDACTED]") if key else value
    if isinstance(value,list): return [safe(v) for v in value]
    if isinstance(value,dict): return {k:safe(v) for k,v in value.items() if k.lower() not in SECRET_FIELDS}
    return value


def reject_secrets(value):
    if isinstance(value,dict):
        if any(k.lower() in SECRET_FIELDS for k in value):
            raise ValueError("Request files must not contain credentials or curl commands")
        for v in value.values(): reject_secrets(v)
    elif isinstance(value,list):
        for v in value: reject_secrets(v)
    elif isinstance(value,str):
        key=os.getenv("RUNNINGHUB_API_KEY")
        if key and key in value: raise ValueError("Credential detected inside request value")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def file_digest(path):
    result=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): result.update(block)
    return result.hexdigest()


def save(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(safe(value),ensure_ascii=False,indent=2),encoding="utf-8")
    temp.replace(path)


def checked_request(request):
    reject_secrets(request)
    if set(request)-{"webappId","nodeInfoList","instanceType"}:
        raise ValueError("Only webappId, nodeInfoList and instanceType are supported")
    if not re.fullmatch(r"\d+",str(request.get("webappId",""))):
        raise ValueError("webappId must come from the selected application's API page")
    if not isinstance(request.get("nodeInfoList"),list) or not request["nodeInfoList"]:
        raise ValueError("nodeInfoList is empty")
    for node in request["nodeInfoList"]:
        if not {"nodeId","fieldName","fieldValue"} <= set(node):
            raise ValueError("Node is missing nodeId, fieldName or fieldValue")
        if any(not isinstance(node[k],str) for k in ("nodeId","fieldName","fieldValue")):
            raise ValueError("Node IDs, field names and values must be strings")
    return hashlib.sha256(json.dumps(request,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


class Client:
    def __init__(self,base):
        self.base=base.rstrip("/")
        if self.base not in ALLOWED_BASES: raise ValueError("Unsupported API origin")

    def post(self,path,payload=None,files=None):
        import requests
        key=os.getenv("RUNNINGHUB_API_KEY")
        if not key: raise ValueError("RUNNINGHUB_API_KEY is not present in this process")
        with requests.Session() as session:
            session.headers["Authorization"]="Bearer "+key
            body=dict(payload or {})
            if path=="/task/openapi/ai-app/run": body["apiKey"]=key
            try:
                response=session.post(self.base+path,json=body if files is None else None,
                                      files=files,timeout=(30,180),allow_redirects=False)
                if response.status_code<200 or response.status_code>=300:
                    raise RuntimeError(f"HTTP {response.status_code}; inspect local task/platform status before retrying")
                result=response.json()
            except requests.RequestException:
                raise RuntimeError("Network failure; submission may already exist. Reconcile pending task") from None
        if result.get("code") not in (None,0,"0",200,"200"):
            # Avoid printing provider responses, which can contain signed URLs or echoed input.
            raise RuntimeError("API rejected request; code="+str(result.get("code")))
        data=result.get("data",result)
        if not isinstance(data,dict): raise RuntimeError("Unexpected API response structure")
        return data


def job_paths(jobs,tag):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}",tag):
        raise ValueError("Use a simple tag with letters, digits, underscores or hyphens")
    root=Path(jobs).resolve(); root.mkdir(parents=True,exist_ok=True)
    return root/f"{tag}.task.json",root/f"{tag}.pending.json"


def submit(jobs,tag,request,client,execute=False):
    fingerprint=checked_request(request)
    # Bind a task to both the payload and the account region.
    fingerprint=hashlib.sha256((client.base+fingerprint).encode()).hexdigest()
    task,pending=job_paths(jobs,tag)
    if task.exists():
        old=read(task)
        if old["request_hash"]!=fingerprint: raise ValueError("Tag already belongs to a different request")
        return {"existing_task":old["taskId"],"submitted":False}
    if pending.exists(): raise ValueError("Unresolved pending submission; reconcile before retrying")
    if not execute:
        return {"dry_run":True,"webappId":request["webappId"],"nodes":len(request["nodeInfoList"]),"request_hash":fingerprint}
    # Exclusive creation is also the concurrency lock. Errors intentionally leave it in place.
    state={"request_hash":fingerprint,"created":time.time(),"base":client.base,"request":request}
    with pending.open("x",encoding="utf-8") as f: json.dump(safe(state),f,ensure_ascii=False)
    if task.exists():
        old=read(task)
        if old["request_hash"]!=fingerprint:
            raise ValueError("Concurrent task belongs to another request; inspect pending state")
        pending.unlink()
        return {"existing_task":old["taskId"],"submitted":False}
    data=client.post("/task/openapi/ai-app/run",request)
    if not data.get("taskId"): raise RuntimeError("Submission returned no taskId; reconcile pending record")
    save(task,{**state,"taskId":str(data["taskId"])})
    pending.unlink()
    return {"taskId":str(data["taskId"]),"submitted":True}


def reconcile(jobs,tag,task_id=None,confirmed=False,note=None):
    task,pending=job_paths(jobs,tag)
    if task.exists(): raise ValueError("Task already recorded; query it instead")
    if not pending.exists(): raise ValueError("No pending submission")
    state=read(pending)
    if task_id:
        if not re.fullmatch(r"\d+",task_id): raise ValueError("Invalid task ID")
        save(task,{**state,"taskId":task_id,"reconciled":time.time()})
    elif confirmed and note and note.strip():
        save(pending.with_name(pending.stem+f".resolved-{time.time_ns()}.json"),
             {**state,"confirmed_not_created":True,"note":note,"resolved":time.time()})
    else: raise ValueError("Provide task-id, or confirmed-not-created with a verification note")
    pending.unlink()
    return {"reconciled":True,"taskId":task_id}


def poll(jobs,tag,client):
    task,_=job_paths(jobs,tag)
    old=read(task)
    if old["base"]!=client.base: raise ValueError("Task API region differs from current --base")
    data=client.post("/openapi/v2/query",{"taskId":old["taskId"]})
    save(task.with_name(f"{tag}.result.json"),data)
    return {"taskId":old["taskId"],"status":data.get("status"),"errorCode":data.get("errorCode"),
            "usage":safe(data.get("usage")),"result_count":len(data.get("results") or [])}


def download(jobs,tag,out):
    import requests
    task,_=job_paths(jobs,tag)
    data=read(task.with_name(f"{tag}.result.json"))
    if data.get("status")!="SUCCESS": raise ValueError("Poll a successful task before downloading")
    dest=Path(out).resolve(); dest.mkdir(parents=True,exist_ok=True)
    manifest=task.with_name(f"{tag}.files.json")
    previous=read(manifest) if manifest.exists() else []
    files=[]
    for index,result in enumerate(data.get("results") or []):
        url=result.get("url") or result.get("fileUrl")
        if not url: continue
        parsed=urlparse(url)
        if parsed.scheme!="https" or parsed.username or parsed.password: raise ValueError("Unexpected result URL")
        ext=Path(parsed.path).suffix.lower()
        if ext not in {".mp4",".mov",".webm",".wav",".mp3",".m4a",".flac",".png",".jpg"}:
            raise ValueError("Unknown result format; inspect locally before downloading")
        path=dest/f"{tag}-{index}{ext}"
        if path.exists():
            recorded=next((f for f in previous if f["path"]==str(path)),None)
            if recorded and recorded.get("sha256")==file_digest(path):
                files.append(recorded)
                continue
            raise ValueError(f"Unverified output already exists: {path.name}; inspect before replacing")
        part=path.with_suffix(ext+".part")
        # A separate session prevents leaking the API bearer token to media/CDN origins.
        with requests.Session() as session:
            session.trust_env=False
            session.auth=None
            session.headers.pop("Authorization",None)
            with session.get(url,stream=True,timeout=(30,180),headers={"Accept-Encoding":"identity"}) as r:
                r.raise_for_status()
                with part.open("wb") as f:
                    for chunk in r.iter_content(1024*1024): f.write(chunk)
        if part.stat().st_size==0: raise RuntimeError("Empty output download")
        part.replace(path)
        files.append({"path":str(path),"bytes":path.stat().st_size,"sha256":file_digest(path)})
        save(manifest,files)
    if not files: raise ValueError("Successful task has no supported output files")
    save(manifest,files)
    return {"files":files}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jobs",required=True);p.add_argument("--base",default="https://www.runninghub.cn")
    sub=p.add_subparsers(dest="command",required=True)
    s=sub.add_parser("upload");s.add_argument("--file",required=True);s.add_argument("--out",required=True)
    s=sub.add_parser("submit");s.add_argument("--tag",required=True);s.add_argument("--request",required=True);s.add_argument("--execute",action="store_true")
    s=sub.add_parser("poll");s.add_argument("--tag",required=True)
    s=sub.add_parser("download");s.add_argument("--tag",required=True);s.add_argument("--out",required=True)
    s=sub.add_parser("reconcile");s.add_argument("--tag",required=True)
    group=s.add_mutually_exclusive_group(required=True);group.add_argument("--task-id");group.add_argument("--confirmed-not-created",action="store_true")
    s.add_argument("--note")
    a=p.parse_args();client=Client(a.base)
    if a.command=="upload":
        path=Path(a.file)
        if not path.is_file(): raise ValueError("Input file does not exist")
        with path.open("rb") as f: data=client.post("/openapi/v2/media/upload/binary",files={"file":(path.name,f)})
        name=data.get("fileName") or data.get("filename")
        if not name: raise RuntimeError("Upload returned no filename")
        save(a.out,{"fileName":name,"uploaded_at":time.time(),"bytes":path.stat().st_size})
        result={"saved":str(a.out),"bytes":path.stat().st_size}
    elif a.command=="submit": result=submit(a.jobs,a.tag,read(a.request),client,a.execute)
    elif a.command=="poll": result=poll(a.jobs,a.tag,client)
    elif a.command=="download": result=download(a.jobs,a.tag,a.out)
    else: result=reconcile(a.jobs,a.tag,a.task_id,a.confirmed_not_created,a.note)
    print(json.dumps(safe(result),ensure_ascii=False))


if __name__=="__main__":
    try: main()
    except Exception as e:
        # Do not print tracebacks/HTTP response bodies that may expose signed URLs or keys.
        if type(e).__module__.startswith("requests"):
            raise SystemExit("Network download failed; inspect local partial file and refresh result query")
        raise SystemExit(str(safe(str(e))))
