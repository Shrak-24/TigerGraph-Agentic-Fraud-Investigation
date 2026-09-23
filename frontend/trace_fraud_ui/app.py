
import streamlit as st
st.set_page_config(page_title="TRACE. — Fraud Investigation Workbench", page_icon=".", layout="wide")
P=["Account takeover","Card / transaction fraud","Identity fraud","Payment fraud","Synthetic / emerging pattern"]
S=["Open","Investigating","Evidence requested","Resolved","Escalated"]
T=["Fraud signal","Customer report","Analyst request"]
cases=[{"id":f"FRD-2026-{i:03d}","customer":f"Customer {i:02d}","account":f"ACCT-{100000+i}","pattern":P[(i-1)%5],"status":S[(i-1)%5],"trigger":T[(i-1)%3],"bank":[78,65,83,91,58][(i-1)%5],"agent":[88,77,86,94,63][(i-1)%5],"conf":[88,81,74,91,63][(i-1)%5]} for i in range(1,21)]
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono&family=Space+Grotesk:wght@400;500;600;700&display=swap');
.stApp{background:#090909;color:#f1eee7}.block-container{max-width:1500px;padding:1.3rem 2.6rem 3rem}section[data-testid=stSidebar]{background:#0c0c0c;border-right:1px solid #292929}
body,[class*="css"]{font-family:"Space Grotesk",sans-serif}.mono{font-family:"DM Mono",monospace}
.k{font-family:"DM Mono",monospace;font-size:.58rem;letter-spacing:.22em;color:#666;text-transform:uppercase}.title{font-size:clamp(4rem,8vw,7rem);line-height:.83;font-weight:700;letter-spacing:-.08em;margin:.6rem 0}.soft{color:#aaa59e}
.meta{border-top:1px solid #303030;padding-top:9px;margin-bottom:14px}.meta small{display:block;color:#666;font-family:"DM Mono",monospace;font-size:.55rem;letter-spacing:.15em;text-transform:uppercase}.meta b{display:block;font-size:.82rem;margin-top:5px}
.panel{border-top:1px solid #292929;padding-top:8px;margin-top:18px;font-family:"DM Mono",monospace;font-size:.62rem;letter-spacing:.13em;text-transform:uppercase;color:#ccc}.entity,.box,.action{border:1px solid #292929;background:#101010;padding:12px}.entity small{color:#666;font-family:"DM Mono",monospace;font-size:.5rem;text-transform:uppercase}.entity b{display:block;font-size:.78rem;margin:6px 0 4px}.muted{color:#777;font-size:.62rem}.event{border-left:1px solid #3b3b3b;padding:0 0 17px 15px;margin-left:7px}.event.add{border-color:#ef4b36}.event small{font-family:"DM Mono",monospace;color:#666;font-size:.5rem}.event b{font-size:.72rem}.event p{color:#999;font-size:.64rem;line-height:1.5;margin:4px 0 0}.action{margin-bottom:8px}.action.after{border-color:#4a3530;background:#141110}.action b{font-size:.72rem}.reason{color:#999;font-size:.64rem;line-height:1.6}.sar{border:1px solid #3a2724;background:#120e0e;padding:12px}
</style>""",unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div style="font-size:22px;font-weight:800;letter-spacing:-.07em">TRACE<span style="color:#ef4b36">.</span></div><div class="k">Fraud intelligence</div>',unsafe_allow_html=True)
    st.divider()
    picked=st.selectbox("BENCHMARK CASES",[c["id"]+" · "+c["pattern"] for c in cases],label_visibility="collapsed")
    case=next(c for c in cases if c["id"]==picked.split(" · ")[0])

st.markdown('<div class="k" style="border-bottom:1px solid #292929;padding-bottom:14px">WORKBENCH &nbsp;&nbsp; EVIDENCE &nbsp;&nbsp; CASE MEMORY &nbsp;&nbsp; REPORTS <span style="float:right">OFFLINE • 20 CASES</span></div>',unsafe_allow_html=True)
l,r=st.columns([1.3,.7],gap="large")
with l:
    st.markdown(f'<div class="k" style="margin-top:35px">Case <b>{case["id"]}</b></div>',unsafe_allow_html=True)
    st.markdown('<div class="title">FRAUD<br><span class="soft">INVESTIGATION.</span></div>',unsafe_allow_html=True)
    st.markdown('<div style="color:#9b9892;font-size:.76rem;line-height:1.7;max-width:650px">Evidence-first investigation workspace showing case progression from signal to targeted evidence, uncertainty reduction and human-approved action.</div>',unsafe_allow_html=True)
with r:
    for a,b in [("Status",case["status"]),("Trigger",case["trigger"]),("Pattern",case["pattern"]),("Updated","18 Sep 2026 • 11:15")]:
        st.markdown(f'<div class="meta"><small>{a}</small><b>{b}</b></div>',unsafe_allow_html=True)
m=st.columns(5)
for col,label,val in zip(m,["Bank risk","Agent assessment","Confidence","Connected entities","Case age"],[f'{case["bank"]}/100',f'{case["agent"]}/100',f'{case["conf"]}%',"5","03h 42m"]):
    with col: st.markdown(f'<div class="meta"><small>{label}</small><b>{val}</b></div>',unsafe_allow_html=True)
st.divider()
a,b=st.columns([1.25,.75],gap="large")
with a:
    st.markdown('<div class="panel">01 / Entities involved</div>',unsafe_allow_html=True)
    e=st.columns(3)
    ents=[("Customer",case["customer"],"Primary account holder"),("Account",case["account"],"Primary account"),("Device","DEV-7F9A","New device fingerprint"),("Account","ACCT-100007","Shared beneficiary"),("Account","ACCT-100014","Shared device attribute"),("Transaction","TX-84A91","Disputed activity")]
    for c,(k,n,d) in zip(e*2,ents):
        with c: st.markdown(f'<div class="entity"><small>{k}</small><b>{n}</b><span class="muted">{d}</span></div>',unsafe_allow_html=True)
    st.markdown('<div class="panel">02 / Evidence timeline</div>',unsafe_allow_html=True)
    events=[("Initial • 09:16 • Transaction history","Velocity anomaly detected","6 transactions within 11 minutes; 4 involved a newly observed beneficiary.",False),("Initial • 09:19 • Device signals","New device fingerprint","Login from a new device; prior device was last seen 31 days earlier.",False),("Initial • 09:22 • Graph traversal","Connected-account overlap","Primary account links to 2 previously reviewed accounts.",False),("Additional • 09:35 • Prior cases","Case-memory match","Two similar cases were confirmed as fraud after targeted verification.",True),("Additional • 09:42 • Customer verification","Activity confirmed unauthorized","Customer did not recognize the device session.",True)]
    for meta,title,desc,add in events:
        st.markdown(f'<div class="event {"add" if add else ""}"><small>{meta}</small><br><b>{title}</b><p>{desc}</p></div>',unsafe_allow_html=True)
    st.markdown('<div class="panel">03 / Fraud pattern & assessment</div>',unsafe_allow_html=True)
    x,y=st.columns(2)
    with x:
        st.markdown(f'<div style="font-size:3rem;font-weight:700;letter-spacing:-.08em">{case["conf"]}%</div>',unsafe_allow_html=True); st.progress(case["conf"]/100)
        st.markdown(f'<div class="reason">Correlated transaction, device and relationship signals align with a <b>{case["pattern"].lower()}</b> pattern.</div>',unsafe_allow_html=True)
    with y:
        st.markdown(f'<div class="meta"><small>Uncertainty</small><b>{"Low" if case["conf"]>=88 else "Medium" if case["conf"]>=72 else "High"}</b></div>',unsafe_allow_html=True)
        st.markdown(f'<div class="meta"><small>Pattern class</small><b>{case["pattern"]}</b></div>',unsafe_allow_html=True)
    st.markdown('<div class="panel">04 / Case progression</div>',unsafe_allow_html=True)
    p=st.columns(4)
    for c,n,t,d in zip(p,["01","02","03","04"],["Signal detected","Evidence requested","Assessment updated","Human decision"],["Initial evidence creates uncertainty.","Target the missing evidence.","Confidence changes with evidence.","Consequential action stays controlled."]):
        with c: st.markdown(f'<div class="meta"><small>Step {n}</small><b>{t}</b><div class="muted">{d}</div></div>',unsafe_allow_html=True)
with b:
    st.markdown('<div class="panel">05 / Case memory</div>',unsafe_allow_html=True)
    for cid,outcome,lesson in [("FRD-2026-004","Confirmed fraud","Customer verification + device evidence supported temporary account controls."),("FRD-2026-008","False positive","Legitimate device change explained the anomaly; transaction was released."),("FRD-2026-012","Escalated","Linked accounts required broader evidence collection and human review.")]:
        st.markdown(f'<div class="box" style="margin-bottom:8px"><b style="font-size:.7rem">{cid} • {case["pattern"]}</b><div class="muted">{outcome}</div><div class="reason">{lesson}</div></div>',unsafe_allow_html=True)
    st.markdown('<div class="panel">06 / Next best action</div>',unsafe_allow_html=True)
    st.markdown('<div class="action"><b>Before additional evidence</b><div class="muted">Pending human approval</div><div class="reason">Monitor account + request customer/device evidence.</div></div><div class="action after"><b>After additional evidence</b><div class="muted">Recommended — not auto-executed</div><div class="reason">Escalate case + place temporary transaction hold.</div></div>',unsafe_allow_html=True)
    st.markdown('<div class="panel">07 / Explainability</div>',unsafe_allow_html=True)
    for q,ans in [("What evidence was used?","Transaction velocity, device novelty, graph links, prior-case similarity and customer verification."),("Why more evidence?","Initial signals could also occur during legitimate device or travel changes."),("Why this action?","New evidence reduces uncertainty while consequential controls remain under analyst approval.")]:
        with st.expander(q): st.write(ans)
    st.markdown('<div class="panel">08 / SAR preview</div>',unsafe_allow_html=True)
    if case["agent"]>=80:
        st.markdown('<div class="sar"><div class="k" style="color:#df6b59">Policy trigger met • Generated report snippet</div></div>',unsafe_allow_html=True)
        st.text_area("SAR",f'Case {case["id"]}: suspected {case["pattern"].lower()}. Activity is supported by transaction, device, graph and prior-case evidence. Analyst review is required before filing.',height=110,label_visibility="collapsed")
    else:
        st.caption("SAR preview hidden for this demo case because the configured policy trigger is not met.")
st.divider();st.markdown('<div class="k">TRACE. / OFFLINE DEMO • Synthetic benchmark data • Human approval required for consequential controls</div>',unsafe_allow_html=True)
