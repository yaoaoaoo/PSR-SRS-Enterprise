import { useState } from 'react';
import { evaluateQueries, candidateCoverage } from '../api/evaluation';
import { ApiError } from '../api/client';
import type { EvaluationResult, CandidateCoverageResult } from '../api/types';
import { ErrorState } from '../components/common/ErrorState';

export default function EvaluationPage() {
  const [tab, setTab] = useState<'queries' | 'coverage'>('queries');
  const [queryId, setQueryId] = useState('query_000001');
  const [ks, setKs] = useState('5,10,20');
  const [evalResult, setEvalResult] = useState<EvaluationResult | null>(null);
  const [evalError, setEvalError] = useState('');
  const [evalLoading, setEvalLoading] = useState(false);

  const [coverageJSON, setCoverageJSON] = useState('{"requests":[{"request_id":"r1","candidate_item_ids":["item_000001"]}]}');
  const [covResult, setCovResult] = useState<CandidateCoverageResult | null>(null);
  const [covError, setCovError] = useState('');
  const [covLoading, setCovLoading] = useState(false);
  const [covParseErr, setCovParseErr] = useState('');

  const runEval = async () => {
    setEvalLoading(true); setEvalError('');
    try {
      const parsedKs = ks.split(',').map(Number).filter(k => k > 0);
      if (parsedKs.length === 0) { setEvalError('At least one valid k required'); return; }
      const resp = await evaluateQueries({ queries: [{ query_id: queryId }], ks: parsedKs });
      setEvalResult(resp.data);
    } catch (e) { setEvalError(e instanceof ApiError ? e.message : String(e)); }
    finally { setEvalLoading(false); }
  };

  const runCoverage = async () => {
    setCovLoading(true); setCovError(''); setCovParseErr('');
    try {
      let parsed;
      try { parsed = JSON.parse(coverageJSON); } catch { setCovParseErr('Invalid JSON format'); setCovLoading(false); return; }
      const resp = await candidateCoverage(parsed);
      setCovResult(resp.data);
    } catch (e) { setCovError(e instanceof ApiError ? e.message : String(e)); }
    finally { setCovLoading(false); }
  };

  return (
    <div>
      <div className="page-header"><h2>Evaluation</h2></div>
      <div className="tabs">
        <button className={`tab ${tab==='queries'?'active':''}`} onClick={()=>setTab('queries')}>Query Evaluation</button>
        <button className={`tab ${tab==='coverage'?'active':''}`} onClick={()=>setTab('coverage')}>Candidate Coverage</button>
      </div>

      {tab === 'queries' && (
        <div className="card">
          <div className="form-row">
            <div className="form-group"><label htmlFor="eval-qid">Query ID</label><input id="eval-qid" value={queryId} onChange={e=>setQueryId(e.target.value)} /></div>
            <div className="form-group"><label htmlFor="eval-ks">Ks (comma-separated)</label><input id="eval-ks" value={ks} onChange={e=>setKs(e.target.value)} /></div>
          </div>
          <button className="primary" onClick={runEval} disabled={evalLoading} style={{marginTop:8}}>{evalLoading?'Running...':'Evaluate'}</button>
          {evalError && <ErrorState title="Error" message={evalError} />}
          {evalResult && (
            <div style={{marginTop:12, fontSize:14}}>
              <p>Queries: {evalResult.query_count} | Took: {evalResult.took_ms}ms</p>
              {evalResult.metrics && <pre style={{background:'#f8f9fa', padding:8, borderRadius:4, overflow:'auto', maxHeight:300}}>{JSON.stringify(evalResult.metrics, null, 2)}</pre>}
            </div>
          )}
        </div>
      )}

      {tab === 'coverage' && (
        <div className="card">
          <div className="form-group"><label htmlFor="cov-json">Request JSON</label>
            <textarea id="cov-json" rows={6} value={coverageJSON} onChange={e=>setCoverageJSON(e.target.value)} style={{fontFamily:'monospace',fontSize:13}} />
          </div>
          {covParseErr && <ErrorState title="JSON Error" message={covParseErr} />}
          <button className="primary" onClick={runCoverage} disabled={covLoading} style={{marginTop:8}}>{covLoading?'Running...':'Submit'}</button>
          {covError && <ErrorState title="Error" message={covError} />}
          {covResult && (
            <div style={{marginTop:12, fontSize:14}}>
              <div className="grid-2">
                <div><span style={{color:'var(--muted)'}}>Eligible:</span> {covResult.eligible_requests}</div>
                <div><span style={{color:'var(--muted)'}}>Covered:</span> {covResult.covered_requests}</div>
                <div><span style={{color:'var(--muted)'}}>Req Coverage:</span> {(covResult.request_level_coverage*100).toFixed(1)}%</div>
                <div><span style={{color:'var(--muted)'}}>Item Recall:</span> {(covResult.item_level_recall*100).toFixed(1)}%</div>
                <div><span style={{color:'var(--muted)'}}>Took:</span> {covResult.took_ms}ms</div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
