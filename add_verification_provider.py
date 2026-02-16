filepath = 'chatbot-rag/frontend/src/App.jsx'

with open(filepath, 'r') as f:
    content = f.read()

changes = 0

# 1. Add verification state for provider side after patientProfileData
old_ppd = '  const [patientProfileData, setPatientProfileData] = useState({});'
new_ppd = '''  const [patientProfileData, setPatientProfileData] = useState({});
  const [patientVerification, setPatientVerification] = useState(null);
  const [verifyRejectReason, setVerifyRejectReason] = useState('');'''

if old_ppd in content and 'patientVerification' not in content:
    content = content.replace(old_ppd, new_ppd, 1)
    changes += 1
    print("[1] Added patientVerification state")

# 2. Load verification data when selecting patient - add after profile-data fetch
old_profile_load = "} catch (e) { \n    setPatientProfileData({}); \n  }"
# More flexible matching
old_load2 = "setPatientProfileData(d.data || {})"
if old_load2 in content:
    new_load2 = """setPatientProfileData(d.data || {});
        // Load verification status
        try {
          const vRes = await fetch(joinUrl(API_BASE, `/api/provider/patients/${patient.id}/verification`), { headers: authHeaders(authToken) });
          if (vRes.ok) { const vd = await vRes.json(); setPatientVerification(vd); }
        } catch { setPatientVerification(null); }"""
    if 'patientVerification' not in content or 'patient.id}/verification' not in content:
        content = content.replace(old_load2, new_load2, 1)
        changes += 1
        print("[2] Added verification load on patient select")

# 3. Add verification card to provider overview - after Emergency Contact, before Parent/Guardian
old_parent_section = '                    {/* Parent / Guardian */}'
new_verification_card = '''                    {/* Identity Verification */}
                    {patientVerification && patientVerification.status !== 'not_submitted' && (
                      <div className={`rounded-2xl border p-6 ${
                        patientVerification.status === 'approved' ? 'border-emerald-900/30 bg-emerald-950/20' :
                        patientVerification.status === 'rejected' ? 'border-red-900/30 bg-red-950/20' :
                        'border-amber-900/30 bg-amber-950/20'
                      }`}>
                        <h4 className={`text-xs font-bold uppercase tracking-widest mb-3 ${
                          patientVerification.status === 'approved' ? 'text-emerald-400' :
                          patientVerification.status === 'rejected' ? 'text-red-400' :
                          'text-amber-400'
                        }`}>Identity Verification — {patientVerification.status.toUpperCase()}</h4>
                        <div className="space-y-3">
                          <div className="flex items-center gap-4 text-xs">
                            {patientVerification.id_document_path && (
                              <a href={joinUrl(API_BASE, `/api/verification/file/${selectedPatient.id}/${patientVerification.id_document_path.split('/').pop()}`)} target="_blank" rel="noopener noreferrer"
                                className="flex items-center gap-2 rounded-lg bg-zinc-800 px-3 py-2 text-indigo-400 hover:bg-zinc-700 transition-colors">
                                <Camera size={14} /> View ID Document
                              </a>
                            )}
                            {patientVerification.video_path && (
                              <a href={joinUrl(API_BASE, `/api/verification/file/${selectedPatient.id}/${patientVerification.video_path.split('/').pop()}`)} target="_blank" rel="noopener noreferrer"
                                className="flex items-center gap-2 rounded-lg bg-zinc-800 px-3 py-2 text-indigo-400 hover:bg-zinc-700 transition-colors">
                                <Eye size={14} /> View Video
                              </a>
                            )}
                          </div>
                          {patientVerification.status === 'pending' && (
                            <div className="flex items-center gap-2 pt-2">
                              <button onClick={async () => {
                                await fetch(joinUrl(API_BASE, `/api/provider/patients/${selectedPatient.id}/verification/review`), {
                                  method: 'POST', headers: { ...authHeaders(authToken), 'Content-Type': 'application/json' },
                                  body: JSON.stringify({ action: 'approve' })
                                });
                                setPatientVerification(v => ({...v, status: 'approved'}));
                              }} className="rounded-lg bg-emerald-600 px-4 py-2 text-xs text-white hover:bg-emerald-500 transition-colors flex items-center gap-1">
                                <Check size={14} /> Approve
                              </button>
                              <div className="flex-1 flex items-center gap-2">
                                <input value={verifyRejectReason} onChange={(e) => setVerifyRejectReason(e.target.value)}
                                  placeholder="Reason (optional)" className="flex-1 rounded-lg bg-zinc-800 border border-zinc-700 px-3 py-2 text-xs outline-none focus:border-red-500/50" />
                                <button onClick={async () => {
                                  await fetch(joinUrl(API_BASE, `/api/provider/patients/${selectedPatient.id}/verification/review`), {
                                    method: 'POST', headers: { ...authHeaders(authToken), 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ action: 'reject', reason: verifyRejectReason })
                                  });
                                  setPatientVerification(v => ({...v, status: 'rejected'}));
                                  setVerifyRejectReason('');
                                }} className="rounded-lg bg-red-600 px-4 py-2 text-xs text-white hover:bg-red-500 transition-colors flex items-center gap-1">
                                  <X size={14} /> Reject
                                </button>
                              </div>
                            </div>
                          )}
                          {patientVerification.status === 'rejected' && patientVerification.rejection_reason && (
                            <p className="text-xs text-red-400/70 italic">Rejection reason: {patientVerification.rejection_reason}</p>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Parent / Guardian */}'''

if old_parent_section in content and 'Identity Verification' not in content:
    content = content.replace(old_parent_section, new_verification_card, 1)
    changes += 1
    print("[3] Added verification review card to provider overview")

# 4. Add auth header helper for file uploads (without Content-Type)
# Already handled in submitVerification using just Authorization header

with open(filepath, 'w') as f:
    f.write(content)

print(f"\nDone! {changes} changes applied")
