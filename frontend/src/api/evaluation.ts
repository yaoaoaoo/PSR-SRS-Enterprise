import { apiPost } from './client';
import type { CandidateCoverageRequest, CandidateCoverageResult, DataResponse, EvaluationQueriesRequest, EvaluationResult } from './types';

export function evaluateQueries(body: EvaluationQueriesRequest, signal?: AbortSignal) {
  return apiPost<EvaluationQueriesRequest, DataResponse<EvaluationResult>>('/evaluation/queries', body, signal);
}

export function candidateCoverage(body: CandidateCoverageRequest, signal?: AbortSignal) {
  return apiPost<CandidateCoverageRequest, DataResponse<CandidateCoverageResult>>('/evaluation/candidate-coverage', body, signal);
}
