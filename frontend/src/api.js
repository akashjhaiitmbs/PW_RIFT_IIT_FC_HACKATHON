const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

/**
 * POST /api/v1/analyze
 *
 * Single call: upload VCF + patient info + drugs → get full results.
 *
 * @param {File}     file                  - The .vcf file
 * @param {string}   patientCode           - Patient identifier string
 * @param {string[]} drugs                 - e.g. ['CODEINE', 'WARFARIN']
 * @param {string[]} concurrentMedications - e.g. ['PAROXETINE']
 * @returns {Promise<object>}              - Full analysis data object
 */
export async function analyzeVCF({ file, patientCode, drugs, concurrentMedications = [] }) {
    const form = new FormData();
    form.append('vcf_file', file);
    form.append('patient_code', patientCode || 'PATIENT_001');
    form.append('drugs', drugs.join(','));
    form.append('concurrent_medications', concurrentMedications.join(','));

    const res = await fetch(`${BASE}/analyze`, { method: 'POST', body: form });
    const json = await res.json();
    if (!res.ok || !json.success) throw new Error(json.error || json.detail?.error || 'Analysis failed');
    return json.data;
}

/**
 * GET /api/v1/results/{patientId}
 *
 * Fetch results for a patient by their UUID or patient_code.
 *
 * @param {string} patientId - UUID or patient_code string
 * @returns {Promise<object>}
 */
export async function getResultsByPatient(patientId) {
    const res = await fetch(`${BASE}/results/${encodeURIComponent(patientId)}`);
    const json = await res.json();
    if (!res.ok || !json.success) throw new Error(json.error || json.detail?.error || 'Failed to fetch results');
    return json.data;
}

/**
 * GET /api/v1/supported-drugs
 *
 * Returns list of { drug, primary_gene } objects.
 */
export async function getSupportedDrugs() {
    const res = await fetch(`${BASE}/supported-drugs`);
    const json = await res.json();
    return json.data || [];
}
