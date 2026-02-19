const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export async function uploadVCF({ file, patientCode }) {
    const form = new FormData();
    form.append('vcf_file', file);
    form.append('patient_code', patientCode || 'PATIENT_001');

    const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form });
    const json = await res.json();
    if (!res.ok || !json.success) throw new Error(json.error || 'Upload failed');
    return json.data;
}

export async function runAnalysis({ vcfUploadId, drugs, concurrentMedications }) {
    const res = await fetch(`${BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            vcf_upload_id: vcfUploadId,
            drugs,
            concurrent_medications: concurrentMedications,
        }),
    });
    const json = await res.json();
    if (!res.ok || !json.success) throw new Error(json.error || 'Analysis failed');
    return json.data;
}

export async function getSupportedDrugs() {
    const res = await fetch(`${BASE}/supported-drugs`);
    const json = await res.json();
    return json.data || [];
}
