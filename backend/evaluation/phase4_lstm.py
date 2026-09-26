"""ASTRA Phase 4 LSTM autoencoder search, freeze, and one-shot holdout evaluation."""
from __future__ import annotations
import argparse, csv, hashlib, json, os, platform, sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any
import numpy as np
from ..data.telemanom import available_channels, load_channel
from .lstm_autoencoder import (TrainOnlyRobustScaler, align_window_scores, freeze_configuration,
    json_safe, make_sequences, persistence_decision, reconstruction_errors, save_model_artifact,
    select_unseen_holdout, train_autoencoder, validation_threshold, verify_frozen_configuration)
from .metrics import calculate_metrics, detection_delays, group_events
from .phase1c import fit_channel, macro_average, predict_channel
from .preprocessing import chronological_split

ROOT=Path('data/external/telemanom'); CONFIG_PATH=Path('backend/evaluation/configs/lstm_experiment.json')
P1_CONFIG=Path('reports/evaluation/phase1c_selected_config.json'); P1_MANIFEST=Path('reports/evaluation/phase1c_holdout_manifest.json'); P1_INVALID=Path('reports/evaluation/phase1c_invalidated_initial_holdout_manifest.json')
REPORT=Path('reports/evaluation'); SEARCH=REPORT/'phase4_lstm_search.json'; DEV_CSV=REPORT/'phase4_lstm_development.csv'; FROZEN=REPORT/'phase4_lstm_frozen_config.json'; MANIFEST=REPORT/'phase4_lstm_holdout_manifest.json'
RESULT=REPORT/'phase4_lstm_holdout_results.json'; RESULT_CSV=REPORT/'phase4_lstm_holdout_results.csv'; MD=REPORT/'PHASE4_LSTM_RESULTS.md'; HISTORY=REPORT/'phase4_lstm_training_history.json'; PLOT=REPORT/'phase4_lstm_reconstruction_examples.svg'; MODEL=Path('artifacts/models/phase4_lstm_autoencoder.pt')
METHODS=('threshold','isolation_forest','combined','lstm_autoencoder'); PRIORITY={m:i for i,m in enumerate(METHODS)}

def read(path): return json.loads(path.read_text(encoding='utf-8'))
def write(path,value): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(json_safe(value),indent=2)+'\n',encoding='utf-8')
def write_csv(path,rows):
    fields=sorted({k for row in rows for k in row}); path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows([{k:json_safe(row.get(k)) for k in fields} for row in rows])
def framework_facts():
    try: import torch
    except ImportError as e: raise RuntimeError('Run Phase 4 inside .venv-dl') from e
    return {'python_version':platform.python_version(),'pytorch_version':torch.__version__,'numpy_version':np.__version__,'device':'cpu','cuda_available':bool(torch.cuda.is_available()),'mkldnn_available':bool(torch.backends.mkldnn.is_available()),'processor':platform.processor(),'logical_cpu_count':os.cpu_count(),'platform':platform.platform(),'environment_size_bytes':sum(path.stat().st_size for path in Path(sys.prefix).rglob('*') if path.is_file()),'framework_selection_reason':'PyTorch provides an official Windows CPU wheel for Python 3.12 and remains isolated from ASTRA production.'}
def peak_memory():
    if os.name!='nt': return None
    try:
        import ctypes
        from ctypes import wintypes
        class C(ctypes.Structure): _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD),('PeakWorkingSetSize',ctypes.c_size_t),('WorkingSetSize',ctypes.c_size_t),('a',ctypes.c_size_t),('b',ctypes.c_size_t),('c',ctypes.c_size_t),('d',ctypes.c_size_t),('e',ctypes.c_size_t),('f',ctypes.c_size_t)]
        c=C(); c.cb=ctypes.sizeof(c); h=ctypes.windll.kernel32.GetCurrentProcess()
        return int(c.PeakWorkingSetSize) if ctypes.windll.psapi.GetProcessMemoryInfo(h,ctypes.byref(c),c.cb) else None
    except (AttributeError,OSError): return None
@dataclass
class Prepared:
    mission:str; channel:str; fit_raw:np.ndarray; val_raw:np.ndarray; scaler:TrainOnlyRobustScaler; fit:np.ndarray; val:np.ndarray
def values(run,names):
    missing=sorted(set(names)-set(run.value_columns))
    if missing: raise ValueError(f'{run.channel_id} lacks {missing}')
    return run.frame[names].to_numpy(float)
def prepare(channel_map,config):
    raw_splits=[]
    for mission,channels in channel_map.items():
        for channel in channels:
            train,_=load_channel(ROOT,channel); raw=values(train,config['selected_features']); fit,val=chronological_split(raw,float(config['fit_fraction'])); raw_splits.append((mission,channel,fit,val))
    scaler=TrainOnlyRobustScaler(float(config['near_constant_epsilon'])).fit(np.concatenate([item[2] for item in raw_splits]),config['selected_features'])
    return [Prepared(mission,channel,fit,val,scaler,scaler.transform(fit),scaler.transform(val)) for mission,channel,fit,val in raw_splits]
def pool(items,window,stride,split):
    batches=[]
    for item in items:
        x=item.fit if split=='fit' else item.val; batch=make_sequences(x,window,stride=stride,boundary_ids=np.full(len(x),item.channel))
        if len(batch.windows): batches.append(batch.windows)
    if not batches: raise ValueError(f'No {split} windows')
    return np.concatenate(batches)
def inject(item):
    x=item.val_raw.copy(); onset=max(1,int(len(x)*.6)); truth=np.zeros(len(x),bool); truth[onset:]=True; scale=max(float(item.scaler.scale_[0]),1e-6); direction=1 if int(hashlib.sha256(f'{item.mission}:{item.channel}'.encode()).hexdigest(),16)%2 else -1; x[onset:,0]+=direction*np.linspace(2*scale,8*scale,len(x)-onset)
    return item.scaler.transform(x),truth
def score(model,x,config,cutoff):
    batch=make_sequences(x,int(config['window_size'])); errors,features=reconstruction_errors(model,batch.windows,int(config['batch_size'])); aligned=align_window_scores(errors,batch.end_indices,len(x)); pred=persistence_decision(np.isfinite(aligned)&(aligned>cutoff),int(config['persistence']))
    return aligned,pred,features
def candidate(base,item,index):
    keys=('selected_features','fit_fraction','scaling','near_constant_epsilon','training_stride','inference_stride','batch_size','learning_rate','max_epochs','early_stopping_patience','early_stopping_min_delta','random_seed','event_matching_tolerance')
    out={k:base[k] for k in keys}; out.update(item); out['configuration_id']=f'lstm-{index:02d}'; return out
def evaluate_candidate(items,config):
    train=pool(items,int(config['window_size']),int(config['training_stride']),'fit'); val=pool(items,int(config['window_size']),1,'val'); started=perf_counter(); model,history=train_autoencoder(train,val,config); training_ms=(perf_counter()-started)*1000
    val_errors,_=reconstruction_errors(model,val,int(config['batch_size'])); cutoff=validation_threshold(val_errors,float(config['threshold_quantile'])); nt=[]; npred=[]; st=[]; spred=[]; channel_f1=[]
    for item in items:
        _,p,_=score(model,item.val,config,cutoff); nt.append(np.zeros(len(item.val),bool)); npred.append(p); synthetic,truth=inject(item); _,p,_=score(model,synthetic,config,cutoff); st.append(truth); spred.append(p); channel_f1.append(float(calculate_metrics([truth],[p],int(config['event_matching_tolerance']))['point_f1']))
    normal=calculate_metrics(nt,npred,int(config['event_matching_tolerance'])); synthetic=calculate_metrics(st,spred,int(config['event_matching_tolerance'])); selection=float(synthetic['point_f1'])-2*float(normal['point_false_positive_rate'])-.002*float(normal['false_alerts_per_1000_observations'])-.1*float(np.std(channel_f1))
    row={**config,'validation_threshold':cutoff,'normal_validation':normal,'synthetic_validation':synthetic,'synthetic_validation_f1_std_across_channels':float(np.std(channel_f1)),'selection_score':selection,'training_time_ms':training_ms,'epochs_completed':len(history),'parameter_count':sum(p.numel() for p in model.parameters()),'train_window_count':len(train),'normal_validation_window_count':len(val)}
    return row,history
def run_search():
    if MANIFEST.exists() or RESULT.exists(): raise FileExistsError('Holdout manifest or result exists; frozen architecture selection cannot be rerun')
    base=read(CONFIG_PATH); items=prepare(base['development_channels'],base); rows=[]; histories={}
    for i,item in enumerate(base['search_grid'],1):
        config=candidate(base,item,i); row,history=evaluate_candidate(items,config); rows.append(row); histories[config['configuration_id']]=history; print(f"{config['configuration_id']}: score={row['selection_score']:.6f} synthetic_f1={row['synthetic_validation']['point_f1']:.6f}",flush=True)
    selected=max(rows,key=lambda r:(r['selection_score'],-r['window_size'],-r['latent_units'],-r['lstm_layers'],r['loss']=='mae',r['persistence'],r['threshold_quantile']))
    keys=('selected_features','fit_fraction','scaling','near_constant_epsilon','training_stride','inference_stride','batch_size','learning_rate','max_epochs','early_stopping_patience','early_stopping_min_delta','random_seed','event_matching_tolerance','window_size','latent_units','lstm_layers','loss','persistence','threshold_quantile')
    frozen={k:selected[k] for k in keys}; frozen.update({'protocol_version':base['protocol_version'],'framework':base['framework'],'architecture':'LSTM encoder, repeated latent vector, LSTM decoder, time-distributed linear output','threshold_method':'Pooled normal-validation reconstruction-error quantile','development_channels':base['development_channels'],'selected_configuration_id':selected['configuration_id'],'selection_rule':base['selection_rule'],'integration_gate_predeclared_before_holdout':base['integration_gate'],'holdout_selection_salt':base['holdout_selection_salt'],'requested_holdout_channels_per_mission':base['requested_holdout_channels_per_mission'],'development_metrics':{'normal_validation':selected['normal_validation'],'synthetic_validation':selected['synthetic_validation'],'selection_score':selected['selection_score']}}); frozen=freeze_configuration(frozen)
    document={'created_utc':datetime.now(timezone.utc).isoformat(),'framework':framework_facts(),'official_test_labels_used_for_selection':False,'synthetic_faults_are_not_nasa_anomalies':True,'search_results':rows,'selected_configuration_id':selected['configuration_id'],'frozen_configuration_sha256':frozen['configuration_sha256'],'training_histories':histories}; write(SEARCH,document); write(FROZEN,frozen)
    flat=[]
    for r in rows: flat.append({'configuration_id':r['configuration_id'],'window_size':r['window_size'],'latent_units':r['latent_units'],'lstm_layers':r['lstm_layers'],'loss':r['loss'],'persistence':r['persistence'],'threshold_quantile':r['threshold_quantile'],'normal_validation_point_fpr':r['normal_validation']['point_false_positive_rate'],'normal_validation_false_alerts_per_1000':r['normal_validation']['false_alerts_per_1000_observations'],'synthetic_validation_precision':r['synthetic_validation']['point_precision'],'synthetic_validation_recall':r['synthetic_validation']['point_recall'],'synthetic_validation_f1':r['synthetic_validation']['point_f1'],'synthetic_validation_event_recall':r['synthetic_validation']['event_recall'],'selection_score':r['selection_score'],'training_time_ms':r['training_time_ms'],'epochs_completed':r['epochs_completed'],'parameter_count':r['parameter_count']})
    write_csv(DEV_CSV,flat); return document
def create_manifest():
    if MANIFEST.exists(): raise FileExistsError(f'Refusing to overwrite {MANIFEST}')
    frozen=read(FROZEN); verify_frozen_configuration(frozen); p1=read(P1_MANIFEST); invalid=read(P1_INVALID); excluded={}
    for mission in ('SMAP','MSL'): excluded[mission]=sorted(set(frozen['development_channels'][mission]+p1['selected_channels'][mission]+invalid['selected_channels'][mission]))
    available={m:available_channels(ROOT,m) for m in ('SMAP','MSL')}; selected,limits=select_unseen_holdout(available,excluded,requested_per_mission=int(frozen['requested_holdout_channels_per_mission']),salt=frozen['holdout_selection_salt'])
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'selection_rule':'Exclude development, Phase 1C final, invalidated Phase 1C, and Phase 4 debug-inspected channels; SHA-256 rank remaining IDs; select up to five per mission.','selected_channels':selected,'excluded_channels':excluded,'phase4_debug_inspected_channels':{'SMAP':[],'MSL':[]},'frozen_configuration_sha256':frozen['configuration_sha256'],'random_seeds':{'model':frozen['random_seed']},'limitations':limits,'performance_not_calculated_when_manifest_written':True}; write(MANIFEST,manifest); return manifest
def aggregate(rows,truths,predictions,tolerance):
    micro={}; macro={}; delays={}; keys=list(truths); macro_keys=('point_precision','point_recall','point_f1','event_recall','point_false_positive_rate','false_alerts_per_1000_observations','mean_detection_delay_observations','median_detection_delay_observations')
    for method in METHODS:
        ts=[truths[k] for k in keys]; ps=[predictions[method][k] for k in keys]; micro[method]=calculate_metrics(ts,ps,tolerance); macro[method]=macro_average([r for r in rows if r['method']==method],macro_keys); d=detection_delays(ts,ps,tolerance); delays[method]={'matches':len(d),'mean':float(np.mean(d)) if d else None,'median':float(np.median(d)) if d else None,'p90':float(np.quantile(d,.9)) if d else None,'maximum':max(d) if d else None}
    wins={m:0 for m in METHODS}
    for key in keys:
        grouped={r['method']:r for r in rows if f"{r['mission']}:{r['channel']}"==key}; winner=max(METHODS,key=lambda m:(grouped[m]['point_f1'],grouped[m].get('event_recall') or 0,-grouped[m]['false_alerts_per_1000_observations'],-PRIORITY[m])); wins[winner]+=1
        for row in grouped.values(): row['best_method']=winner
    return {'micro':micro,'macro':macro,'detection_delay_distribution':delays,'channel_wins':wins}
def svg_plot(traces):
    width=900; rowh=230; margin=55; height=max(280,rowh*len(traces)); parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">','<rect width="100%" height="100%" fill="#101010"/>','<style>text{font-family:Arial;fill:#ddd;font-size:12px}.axis{stroke:#777}.score{fill:none;stroke:#f4f3ee;stroke-width:1.5}.threshold{stroke:#d3a15f;stroke-dasharray:5 4}.truth{fill:#9e4b45;opacity:.18}</style>']
    for row,t in enumerate(traces):
        y0=row*rowh+35; scores=np.asarray(t['scores']); finite=scores[np.isfinite(scores)]; top=max(float(np.max(finite)) if len(finite) else 1,float(t['threshold']))*1.05; x=lambda i:margin+i*(width-2*margin)/max(1,len(scores)-1); y=lambda v:y0+155-min(float(v),top)*150/max(top,1e-9)
        parts += [f'<text x="{margin}" y="{y0-12}">{t["mission"]} {t["channel"]} reconstruction error</text>',f'<line class="axis" x1="{margin}" y1="{y0+155}" x2="{width-margin}" y2="{y0+155}"/>']
        for a,b in t['truth_intervals']: parts.append(f'<rect class="truth" x="{x(a):.2f}" y="{y0}" width="{max(1,x(b)-x(a)):.2f}" height="155"/>')
        points=' '.join(f'{x(i):.2f},{y(v):.2f}' for i,v in enumerate(scores) if np.isfinite(v)); parts += [f'<polyline class="score" points="{points}"/>',f'<line class="threshold" x1="{margin}" y1="{y(t["threshold"]):.2f}" x2="{width-margin}" y2="{y(t["threshold"]):.2f}"/>']
    parts.append('</svg>'); PLOT.write_text('\n'.join(parts)+'\n',encoding='utf-8')
def run_holdout():
    if RESULT.exists(): raise FileExistsError(f'Final holdout exists; refusing rerun: {RESULT}')
    frozen=read(FROZEN); verify_frozen_configuration(frozen); manifest=read(MANIFEST)
    if manifest['frozen_configuration_sha256']!=frozen['configuration_sha256']: raise ValueError('Manifest/config hash mismatch')
    p1=read(P1_CONFIG); items=prepare(manifest['selected_channels'],frozen); train=pool(items,int(frozen['window_size']),int(frozen['training_stride']),'fit'); val=pool(items,int(frozen['window_size']),1,'val'); started=perf_counter(); model,history=train_autoencoder(train,val,frozen); training_ms=(perf_counter()-started)*1000; val_errors,_=reconstruction_errors(model,val,int(frozen['batch_size'])); cutoff=validation_threshold(val_errors,float(frozen['threshold_quantile'])); artifact=save_model_artifact(model,MODEL,{'frozen_configuration_sha256':frozen['configuration_sha256'],'validation_threshold':cutoff,'retained_features':frozen['selected_features']})
    truths={}; predictions={m:{} for m in METHODS}; rows=[]; timings={m:0.0 for m in METHODS}; traces=[]; evidence=[]; audits=[]; prepared={f'{i.mission}:{i.channel}':i for i in items}
    for mission,channels in manifest['selected_channels'].items():
        for channel in channels:
            key=f'{mission}:{channel}'; train_run,test=load_channel(ROOT,channel); train_values=train_run.frame[train_run.value_columns].to_numpy(float); test_values=test.frame[test.value_columns].to_numpy(float); truth=test.frame.ground_truth_anomaly.to_numpy(bool); truths[key]=truth
            state=fit_channel(train_values,p1); hist=train_values[-max(0,int(p1['rolling_window'])-1):]; masks,times=predict_channel(state,test_values,p1,hist)
            for method in METHODS[:3]: predictions[method][key]=masks[method]; timings[method]+=float(times[method])
            item=prepared[key]; scaled=item.scaler.transform(values(test,frozen['selected_features'])); began=perf_counter(); errors,pred,feature_errors=score(model,scaled,frozen,cutoff); timings['lstm_autoencoder']+=(perf_counter()-began)*1000; predictions['lstm_autoencoder'][key]=pred; audits.append({'mission':mission,'channel':channel,'retained_features':item.scaler.retained_features,'removed_features':item.scaler.removed_features,'fit_observations':len(item.fit_raw),'validation_observations':len(item.val_raw)})
            found=np.flatnonzero(pred); confirmed=int(found[0]) if len(found) else None; feature_map={n:float(v) for n,v in zip(item.scaler.retained_features,feature_errors,strict=True)}; evidence.append({'mission':mission,'channel':channel,'validation_threshold':cutoff,'first_alert_confirmation_index':confirmed,'error_at_first_confirmation':float(errors[confirmed]) if confirmed is not None else None,'window_start_index':confirmed-int(frozen['window_size'])+1 if confirmed is not None else None,'window_end_index':confirmed,'persistence_count':int(frozen['persistence']),'per_feature_reconstruction_error':feature_map,'highest_error_features':sorted(feature_map,key=feature_map.get,reverse=True)[:3],'explanation':'High reconstruction error means the sequence differed from learned normal behaviour. It does not identify a confirmed root cause.'})
            if len(traces)<2: traces.append({'mission':mission,'channel':channel,'scores':errors,'threshold':cutoff,'truth_intervals':[(e.start,e.end) for e in group_events(truth)]})
            metrics={m:calculate_metrics([truth],[predictions[m][key]],int(frozen['event_matching_tolerance'])) for m in METHODS}
            for method in METHODS: rows.append({'mission':mission,'channel':channel,'method':method,**metrics[method]})
    agg=aggregate(rows,truths,predictions,int(frozen['event_matching_tolerance'])); tm=agg['macro']['threshold']; lm=agg['macro']['lstm_autoencoder']; ti=agg['micro']['threshold']; li=agg['micro']['lstm_autoencoder']; gate=frozen['integration_gate_predeclared_before_holdout']; improved=agg['channel_wins']['lstm_autoencoder']; checks={'macro_f1_gain':float(lm['point_f1'] or 0)-float(tm['point_f1'] or 0)>=float(gate['macro_f1_improvement_over_threshold']),'event_recall_not_lower':float(li['event_recall'] or 0)>=float(ti['event_recall'] or 0),'false_alert_limit':float(li['false_alerts_per_1000_observations'])<=float(ti['false_alerts_per_1000_observations'])*float(gate['maximum_false_alert_ratio_to_threshold']),'practical_inference':timings['lstm_autoencoder']<60000,'improvement_spans_multiple_channels':improved>=2}; passed=all(checks.values())
    result={'run_date_utc':datetime.now(timezone.utc).isoformat(),'experiment_status':'Offline public telemetry research evaluation; not operational validation','framework':framework_facts(),'manifest':manifest,'frozen_configuration':frozen,'validation_reconstruction_threshold':cutoff,'training_time_ms':{'lstm_autoencoder':training_ms},'inference_time_ms':timings,'peak_process_working_set_bytes':peak_memory(),'model_artifact':artifact,'model_parameter_count':sum(p.numel() for p in model.parameters()),'train_window_count':len(train),'validation_window_count':len(val),'scaler_audit':audits,**agg,'per_channel':rows,'reconstruction_evidence':evidence,'phase5_eligibility_gate':{'predeclared_gate':gate,'checks':checks,'passed':passed},'recommendation':'Eligible only for optional experimental integration; robust thresholds remain the operational candidate pending further validation.' if passed else 'Do not integrate the LSTM into the live prototype. Preserve it as research evidence and retain the robust threshold baseline as the recommended operational candidate.','limitations':manifest['limitations']+['Telemanom telemetry is anonymized and pre-scaled upstream.','Only primary telemetry value_0 is shared across SMAP and MSL; anonymized command inputs were excluded from the pooled model.','Public training arrays are treated as normal because official training interval labels are unavailable.','Synthetic validation ramps test one artificial sensitivity pattern and are not NASA anomalies.','This frozen holdout is initial research evidence, not operational validation.']}
    write(RESULT,result); write_csv(RESULT_CSV,rows); write(HISTORY,{'frozen_configuration_sha256':frozen['configuration_sha256'],'history':history}); svg_plot(traces); write_report(result); return result
def fmt(v): return '—' if v is None else f'{v:.6f}' if isinstance(v,float) else str(v)
def write_report(r):
    f=r['frozen_configuration']; hw=r['framework']; lines=['# ASTRA Phase 4 LSTM autoencoder results','','Offline research on anonymized, pre-scaled public telemetry. This is not operational validation and is not integrated into the simulator, API, dashboard, or deployment.','','## Framework and hardware','',f"- Python {hw['python_version']}; PyTorch {hw['pytorch_version']}; NumPy {hw['numpy_version']}",f"- Device: CPU; MKL-DNN: {hw['mkldnn_available']}; CUDA: {hw['cuda_available']}",f"- Processor: {hw['processor']}; logical CPUs: {hw['logical_cpu_count']}",f"- {hw['framework_selection_reason']}",'','## Dataset and separation','','Telemanom SMAP/MSL arrays are anonymized and pre-scaled. Each official training array was split chronologically: first 70% for scaler/model fitting and final 30% for normal validation and threshold selection. Official test labels were not used for model or threshold selection.','','Development channels: SMAP A-1, A-2, A-3; MSL C-1, C-2, D-14. Synthetic validation ramps are artificial sensitivity checks, not NASA anomalies.','','Final holdout:']
    for mission,channels in r['manifest']['selected_channels'].items(): lines.append(f"- {mission}: {', '.join(channels)}")
    dev=f['development_metrics']; lines += ['','## Development selection','',f"- Selected configuration: {f['selected_configuration_id']}",f"- Normal-validation point FPR: {dev['normal_validation']['point_false_positive_rate']:.6f}; false alerts/1,000: {dev['normal_validation']['false_alerts_per_1000_observations']:.6f}",f"- Separately labelled synthetic-ramp F1: {dev['synthetic_validation']['point_f1']:.6f}; event recall: {dev['synthetic_validation']['event_recall']:.6f}",'- Synthetic validation results are sensitivity checks, not NASA anomaly performance.']
    lines += ['','## Window construction and model','',f"- Window {f['window_size']}; training stride {f['training_stride']}; inference stride 1",'- Windows never cross channel boundaries. Each score belongs to its window end; the first window_size - 1 observations remain unscored.',f"- Features: {', '.join(f['selected_features'])}; pooled-channel train-fit median/MAD scaling; globally train-constant removal",f"- {f['architecture']}",f"- Latent units {f['latent_units']}; layers {f['lstm_layers']}; loss {f['loss']}",f"- Maximum epochs {f['max_epochs']}; early-stopping patience {f['early_stopping_patience']}; batch {f['batch_size']}",f"- Normal-validation quantile {f['threshold_quantile']}; threshold {r['validation_reconstruction_threshold']:.6f}; persistence {f['persistence']}",f"- Frozen SHA-256 `{f['configuration_sha256']}`",'','## Final comparison','','| Method | Micro precision | Micro recall | Micro F1 | Macro precision | Macro recall | Macro F1 | Event recall | Point FPR | False alerts/1,000 | Mean delay | Median delay | P90 delay |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for m in METHODS:
        a=r['micro'][m]; b=r['macro'][m]; d=r['detection_delay_distribution'][m]; lines.append(f"| {m} | {fmt(a['point_precision'])} | {fmt(a['point_recall'])} | {fmt(a['point_f1'])} | {fmt(b['point_precision'])} | {fmt(b['point_recall'])} | {fmt(b['point_f1'])} | {fmt(a['event_recall'])} | {fmt(a['point_false_positive_rate'])} | {fmt(a['false_alerts_per_1000_observations'])} | {fmt(d['mean'])} | {fmt(d['median'])} | {fmt(d['p90'])} |")
    lines += ['',f"Per-channel winner count: `{r['channel_wins']}`.",'','## Per-channel metrics','','| Mission | Channel | Method | F1 | Event recall | Point FPR | False alerts/1,000 | Mean delay | Winner |','|---|---|---|---:|---:|---:|---:|---:|---|']
    for row in r['per_channel']: lines.append(f"| {row['mission']} | {row['channel']} | {row['method']} | {fmt(row['point_f1'])} | {fmt(row['event_recall'])} | {fmt(row['point_false_positive_rate'])} | {fmt(row['false_alerts_per_1000_observations'])} | {fmt(row['mean_detection_delay_observations'])} | {row['best_method']} |")
    lines += ['','## Reconstruction evidence','','High reconstruction error means the sequence differed from learned normal behaviour. It does not identify a confirmed root cause.',f"Timeline: `{PLOT.as_posix()}`. JSON evidence includes thresholds, window bounds, confirmation errors, persistence, and per-feature errors.",'','## Runtime and artifact','',f"- Training: {r['training_time_ms']['lstm_autoencoder']:.3f} ms",f"- Inference (threshold / Isolation Forest / combined / LSTM): {r['inference_time_ms']['threshold']:.3f} / {r['inference_time_ms']['isolation_forest']:.3f} / {r['inference_time_ms']['combined']:.3f} / {r['inference_time_ms']['lstm_autoencoder']:.3f} ms",f"- Peak process working set: {r['peak_process_working_set_bytes'] if r['peak_process_working_set_bytes'] is not None else 'unavailable from the Windows process API'}",f"- Isolated environment size: {r['framework']['environment_size_bytes']} bytes",f"- Parameters: {r['model_parameter_count']}",f"- Artifact: {r['model_artifact']['size_bytes']} bytes; SHA-256 `{r['model_artifact']['sha256']}`",'','## Phase 5 eligibility gate','']
    for name,ok in r['phase5_eligibility_gate']['checks'].items(): lines.append(f"- [{'x' if ok else ' '}] {name}")
    lines += ['',f"Overall: **{'passed' if r['phase5_eligibility_gate']['passed'] else 'failed'}**.",r['recommendation'],'','## False-alert and delay trade-offs','',f"No point adjustment was used. LSTM false alerts were {r['micro']['lstm_autoencoder']['false_alerts_per_1000_observations']:.6f}/1,000 versus {r['micro']['threshold']['false_alerts_per_1000_observations']:.6f} for thresholds, but event recall fell from {r['micro']['threshold']['event_recall']:.6f} to {r['micro']['lstm_autoencoder']['event_recall']:.6f}. Median matched-event delay increased from {r['detection_delay_distribution']['threshold']['median']:.1f} to {r['detection_delay_distribution']['lstm_autoencoder']['median']:.1f} observations. This is a lower-alert, lower-sensitivity trade-off, not a win.",'','## Limitations','']+[f'- {x}' for x in r['limitations']]+['','## Reproduction','','```powershell','cd C:\\ASTRA','.\\.venv312\\Scripts\\python.exe -m venv .venv-dl','.\\.venv-dl\\Scripts\\python.exe -m pip install -r backend\\requirements-dl.txt','.\\.venv-dl\\Scripts\\python.exe -m backend.evaluation.phase4_lstm search','.\\.venv-dl\\Scripts\\python.exe -m backend.evaluation.phase4_lstm manifest','# Final holdout is one-shot and refuses overwrite.','.\\.venv-dl\\Scripts\\python.exe -m backend.evaluation.phase4_lstm holdout','```','']
    MD.write_text('\n'.join(lines),encoding='utf-8')
def main():
    p=argparse.ArgumentParser(); p.add_argument('phase',choices=('search','manifest','holdout')); args=p.parse_args()
    if args.phase=='search': out=run_search(); print(json.dumps({'selected_configuration_id':out['selected_configuration_id'],'frozen_configuration_sha256':out['frozen_configuration_sha256']},indent=2))
    elif args.phase=='manifest': print(json.dumps(create_manifest(),indent=2))
    else:
        out=run_holdout(); print(json.dumps({'phase5_gate_passed':out['phase5_eligibility_gate']['passed'],'recommendation':out['recommendation']},indent=2))
if __name__=='__main__': main()
