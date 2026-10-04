from flask import abort
from ..extensions import db
from ..models.planning import TaskPlan, TaskRevision

FIELDS = ('title','description','assigned_to','priority','deadline','status','progress','estimated_duration')

def fields(task):
    value = task.to_dict()
    return {key:value[key] for key in FIELDS}

def snapshot(task):
    if not db.session.scalar(db.select(TaskRevision).filter_by(task_id=task.id,version=task.version)):
        db.session.add(TaskRevision(task_id=task.id, version=task.version, fields=fields(task)))

def duration(value):
    if type(value) not in (int,float) or not 0.25 <= value <= 365:
        abort(400, description='Estimated duration must be 0.25–365 working days.')
    return float(value)

def set_duration(task, value):
    value=duration(value)
    if not task.plan: task.plan=TaskPlan(duration=value)
    else: task.plan.duration=value

def graph(project):
    tasks={t.id:t for t in project.tasks}
    predecessors={i:[d.depends_on_id for d in t.dependencies] for i,t in tasks.items()}
    ordered=[]; pending=set(tasks)
    while pending:
        ready=sorted(i for i in pending if all(p in ordered for p in predecessors[i]))
        if not ready: abort(409, description='Dependency cycle detected.')
        ordered.extend(ready); pending.difference_update(ready)
    return tasks, predecessors, ordered

def insights(project, day, members):
    tasks, predecessors, ordered=graph(project)
    start={}; finish={}; parent={}
    for i in ordered:
        p=max(predecessors[i],key=lambda x:finish[x],default=None)
        parent[i]=p; start[i]=finish[p] if p else 0
        t=tasks[i]
        remaining=0 if t.status=='DONE' else (t.plan.duration if t.plan else 1)*(1-t.progress/100)
        finish[i]=round(start[i]+remaining,3)
    end=max(ordered,key=lambda i:finish[i],default=None); chain=[]
    while end is not None:
        if tasks[end].status!='DONE': chain.insert(0,end)
        end=parent[end]
    span=max(finish.values(),default=0)
    latest={}
    for i in reversed(ordered):
        successors=[j for j in ordered if i in predecessors[j]]
        latest[i]=min((latest[j] for j in successors),default=span)-(finish[i]-start[i])
    critical=[i for i in ordered if tasks[i].status!='DONE' and abs(latest[i]-start[i])<.001]
    active=[t for t in tasks.values() if t.status!='DONE']; n=max(len(tasks),1)
    overdue=[t for t in active if t.deadline and t.deadline<day]
    blocked=[t for t in active if any(tasks[p].status!='DONE' for p in predecessors[t.id])]
    soon=[t for t in active if t.deadline and 0 <= (t.deadline-day).days <= 3]
    urgent=[t for t in active if t.priority=='URGENT']
    overloaded=[m for m in members if m['workload']=='Overloaded']
    deductions=[dict(label='Overdue tasks',points=round(35*len(overdue)/n)),dict(label='Blocked tasks',points=round(20*len(blocked)/n)),dict(label='Deadlines within three days',points=round(10*len(soon)/n)),dict(label='Urgent unfinished work',points=round(10*len(urgent)/n)),dict(label='Overloaded teammates',points=min(15,5*len(overloaded)))]
    if project.deadline and active and (project.deadline-day).days<span:
        deductions.append(dict(label='Remaining critical path exceeds calendar time to deadline',points=15))
    score=max(0,100-sum(d['points'] for d in deductions))
    risks=[]
    for label,items in [('Overdue',overdue),('Blocked by unfinished prerequisites',blocked),('Due within three days',soon),('Urgent unfinished work',urgent)]:
        risks.extend(dict(label=label,task_id=t.id,title=t.title) for t in items)
    risks.extend(dict(label='Member overload',user_id=m['user']['id'],title=m['user']['name']) for m in overloaded)
    risks.extend(dict(label='Overdue critical task',task_id=t.id,title=t.title) for t in overdue if t.id in critical)
    return dict(blocked=len(blocked),health=dict(score=score,label='Healthy' if score>=85 else 'Watch' if score>=65 else 'At Risk' if score>=40 else 'Critical',deductions=deductions),risks=risks,critical_path=dict(task_ids=chain,critical_ids=critical,remaining_days=round(span,2),default_duration_days=1,edges=[dict(from_id=p,to_id=i) for i in ordered for p in predecessors[i]],schedule=[dict(task_id=i,start=start[i],finish=finish[i],slack=round(max(0,latest[i]-start[i]),3)) for i in ordered]))
