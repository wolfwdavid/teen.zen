filepath = 'chatbot-rag/frontend/src/App.jsx'

with open(filepath, 'r') as f:
    lines = f.readlines()

# Line 1776 is the ternary: ) : activeChannel === 'overview' ? (
# Lines 1777-1818 are the old overview content
# Line 1819 starts: ) : activeChannel === 'presenting' ? (

# Find exact boundaries
start = None
end = None
for i, line in enumerate(lines):
    if "activeChannel === 'overview'" in line and '?' in line and start is None:
        start = i + 1  # line after the ternary
    if start and i > start and "activeChannel === 'presenting'" in line:
        end = i
        break

if start is None or end is None:
    print(f"Could not find overview boundaries. start={start}, end={end}")
    exit(1)

print(f"Replacing lines {start+1} to {end} (0-indexed: {start} to {end-1})")

new_overview = '''                  /* ===== OVERVIEW ===== */
                  <div className="max-w-2xl space-y-6">
                    {/* Profile Card */}
                    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">
                      <div className="flex items-center gap-4 mb-4">
                        <div className="h-16 w-16 rounded-2xl overflow-hidden bg-indigo-600/20 text-indigo-400 flex items-center justify-center text-2xl font-bold">
                          {selectedPatient.profile_pic
                            ? <img src={selectedPatient.profile_pic} alt="" className="h-full w-full object-cover" />
                            : capitalize(selectedPatient.username).charAt(0)
                          }
                        </div>
                        <div>
                          <h3 className="text-lg font-bold text-zinc-100">{patientProfileData.fullName || capitalize(selectedPatient.username)}</h3>
                          <p className="text-sm text-zinc-500">{selectedPatient.email}</p>
                          <div className="flex items-center gap-3 mt-1 flex-wrap">
                            {patientProfileData.pronouns && <span className="text-xs text-indigo-400/70 bg-indigo-500/10 px-2 py-0.5 rounded-full">{patientProfileData.pronouns}</span>}
                            {patientProfileData.dob && <p className="text-xs text-zinc-500">DOB: {patientProfileData.dob}</p>}
                            {selectedPatient.age && <p className="text-xs text-zinc-500">Age: {selectedPatient.age}</p>}
                          </div>
                          {(patientProfileData.contactPhone || patientProfileData.contactEmail) && (
                            <div className="flex items-center gap-3 mt-1">
                              {patientProfileData.contactPhone && <p className="text-xs text-zinc-500">Phone: {patientProfileData.contactPhone}</p>}
                              {patientProfileData.contactEmail && <p className="text-xs text-zinc-500">Email: {patientProfileData.contactEmail}</p>}
                            </div>
                          )}
                          {patientProfileData.preferredName && <p className="text-xs text-zinc-600 mt-0.5">Goes by: {patientProfileData.preferredName}</p>}
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-xs">
                        <div className="rounded-xl bg-zinc-950/50 p-3 border border-zinc-800">
                          <p className="text-zinc-500 text-[10px] uppercase tracking-widest font-bold mb-1">Joined</p>
                          <p className="text-zinc-300">{selectedPatient.created_at ? new Date(selectedPatient.created_at).toLocaleDateString() : 'N/A'}</p>
                        </div>
                        <div className="rounded-xl bg-zinc-950/50 p-3 border border-zinc-800">
                          <p className="text-zinc-500 text-[10px] uppercase tracking-widest font-bold mb-1">Last Active</p>
                          <p className="text-zinc-300">{selectedPatient.last_login ? new Date(selectedPatient.last_login).toLocaleDateString() : 'N/A'}</p>
                        </div>
                        <div className="rounded-xl bg-zinc-950/50 p-3 border border-zinc-800">
                          <p className="text-zinc-500 text-[10px] uppercase tracking-widest font-bold mb-1">Distress Level</p>
                          <p className="text-zinc-300 font-mono">{patientIntake.distressLevel ?? '\\u2014'} / 10</p>
                        </div>
                        <div className="rounded-xl bg-zinc-950/50 p-3 border border-zinc-800">
                          <p className="text-zinc-500 text-[10px] uppercase tracking-widest font-bold mb-1">Assigned</p>
                          <p className="text-zinc-300">{selectedPatient.assigned_at ? new Date(selectedPatient.assigned_at).toLocaleDateString() : 'N/A'}</p>
                        </div>
                      </div>
                    </div>

                    {/* Emergency Contact */}
                    {(patientProfileData.emergencyName || patientProfileData.emergencyPhone) && (
                      <div className="rounded-2xl border border-amber-900/30 bg-amber-950/20 p-6">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-amber-400 mb-3">Emergency Contact</h4>
                        <div className="grid grid-cols-3 gap-3 text-xs">
                          {patientProfileData.emergencyName && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Name</p><p className="text-zinc-300">{patientProfileData.emergencyName}</p></div>}
                          {patientProfileData.emergencyRelation && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Relationship</p><p className="text-zinc-300">{patientProfileData.emergencyRelation}</p></div>}
                          {patientProfileData.emergencyPhone && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Phone</p><p className="text-zinc-300">{patientProfileData.emergencyPhone}</p></div>}
                        </div>
                      </div>
                    )}

                    {/* Parent / Guardian */}
                    {patientProfileData.parent1FullName && (
                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Parent / Guardian</h4>
                        <div className="space-y-4">
                          <div>
                            <p className="text-xs text-zinc-400 font-semibold mb-2">Guardian 1</p>
                            <div className="grid grid-cols-2 gap-3 text-xs">
                              <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Name</p><p className="text-zinc-300">{patientProfileData.parent1FullName}{patientProfileData.parent1PreferredName ? ` (${patientProfileData.parent1PreferredName})` : ''}</p></div>
                              {patientProfileData.parent1Pronouns && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Pronouns</p><p className="text-zinc-300">{patientProfileData.parent1Pronouns}</p></div>}
                              {patientProfileData.parent1ContactPhone && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Phone</p><p className="text-zinc-300">{patientProfileData.parent1ContactPhone}</p></div>}
                              {patientProfileData.parent1ContactEmail && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Email</p><p className="text-zinc-300">{patientProfileData.parent1ContactEmail}</p></div>}
                              {patientProfileData.parent1EmergencyRelation && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Relationship</p><p className="text-zinc-300">{patientProfileData.parent1EmergencyRelation}</p></div>}
                            </div>
                          </div>
                          {patientProfileData.parent2FullName && (
                            <div>
                              <p className="text-xs text-zinc-400 font-semibold mb-2">Guardian 2</p>
                              <div className="grid grid-cols-2 gap-3 text-xs">
                                <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Name</p><p className="text-zinc-300">{patientProfileData.parent2FullName}{patientProfileData.parent2PreferredName ? ` (${patientProfileData.parent2PreferredName})` : ''}</p></div>
                                {patientProfileData.parent2ContactPhone && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Phone</p><p className="text-zinc-300">{patientProfileData.parent2ContactPhone}</p></div>}
                                {patientProfileData.parent2ContactEmail && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Email</p><p className="text-zinc-300">{patientProfileData.parent2ContactEmail}</p></div>}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Consent & Logistics */}
                    {(patientProfileData.sessionFormat || patientProfileData.paymentInfo || patientProfileData.consentAcknowledged) && (
                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Consent & Logistics</h4>
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Informed Consent</p><p className={patientProfileData.consentAcknowledged ? "text-emerald-400" : "text-red-400"}>{patientProfileData.consentAcknowledged ? "Acknowledged" : "Not yet"}</p></div>
                          <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Confidentiality</p><p className={patientProfileData.confidentialityExplained ? "text-emerald-400" : "text-red-400"}>{patientProfileData.confidentialityExplained ? "Explained" : "Not yet"}</p></div>
                          {patientProfileData.sessionFormat && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Session Format</p><p className="text-zinc-300">{patientProfileData.sessionFormat}</p></div>}
                          {patientProfileData.paymentInfo && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Payment / Insurance</p><p className="text-zinc-300">{patientProfileData.paymentInfo}</p></div>}
                        </div>
                      </div>
                    )}

                    {/* Presenting Concern */}
                    {patientIntake.whatBringsYou && (
                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Presenting Concern</h4>
                        <p className="text-sm text-zinc-300 leading-relaxed">{patientIntake.whatBringsYou}</p>
                        {patientIntake.whyNow && <p className="text-sm text-zinc-400 mt-2 italic">Why now: {patientIntake.whyNow}</p>}
                      </div>
                    )}

                    {/* Risk & Safety */}
                    {(patientIntake.thoughtsHarmSelf || patientIntake.thoughtsHarmOthers || patientIntake.selfHarmHistory) && (
                      <div className="rounded-2xl border border-red-900/30 bg-red-950/20 p-6">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-red-400 mb-3">Risk & Safety</h4>
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          {patientIntake.thoughtsHarmSelf && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Self-Harm Thoughts</p><p className="text-zinc-300">{patientIntake.thoughtsHarmSelf}</p></div>}
                          {patientIntake.thoughtsHarmOthers && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Harm to Others</p><p className="text-zinc-300">{patientIntake.thoughtsHarmOthers}</p></div>}
                          {patientIntake.selfHarmHistory && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Self-Harm History</p><p className="text-zinc-300">{patientIntake.selfHarmHistory}</p></div>}
                          {patientIntake.currentPlans && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Current Plans</p><p className="text-zinc-300">{patientIntake.currentPlans}</p></div>}
                          {patientIntake.protectiveFactors && <div className="col-span-2"><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Protective Factors</p><p className="text-zinc-300">{patientIntake.protectiveFactors}</p></div>}
                        </div>
                      </div>
                    )}

                    {/* Clinical History */}
                    {(patientIntake.medications || patientIntake.pastDiagnoses || patientIntake.previousTherapy) && (
                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Clinical History</h4>
                        <div className="space-y-3 text-xs">
                          {patientIntake.pastDiagnoses && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Past Diagnoses</p><p className="text-zinc-300">{patientIntake.pastDiagnoses}</p></div>}
                          {patientIntake.medications && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Medications</p><p className="text-zinc-300">{patientIntake.medications}</p></div>}
                          {patientIntake.previousTherapy && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Previous Therapy</p><p className="text-zinc-300">{patientIntake.previousTherapy}</p></div>}
                        </div>
                      </div>
                    )}

                    {/* Life Context */}
                    {(patientIntake.occupation || patientIntake.livingSituation || patientIntake.romanticStatus) && (
                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Life Context</h4>
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          {patientIntake.occupation && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Occupation</p><p className="text-zinc-300">{patientIntake.occupation}</p></div>}
                          {patientIntake.romanticStatus && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Relationship</p><p className="text-zinc-300">{patientIntake.romanticStatus}</p></div>}
                          {patientIntake.livingSituation && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Living Situation</p><p className="text-zinc-300">{patientIntake.livingSituation}</p></div>}
                          {patientIntake.safetyAtHome && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Safety at Home</p><p className="text-zinc-300">{patientIntake.safetyAtHome}</p></div>}
                          {patientIntake.familyDynamics && <div className="col-span-2"><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Family Dynamics</p><p className="text-zinc-300">{patientIntake.familyDynamics}</p></div>}
                        </div>
                      </div>
                    )}

                    {/* Coping & Strengths */}
                    {(patientIntake.copingWhenStressed || patientIntake.personalStrengths || patientIntake.substanceUse) && (
                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Coping & Strengths</h4>
                        <div className="space-y-3 text-xs">
                          {patientIntake.copingWhenStressed && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Coping When Stressed</p><p className="text-zinc-300">{patientIntake.copingWhenStressed}</p></div>}
                          {patientIntake.substanceUse && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Substance Use</p><p className="text-zinc-300">{patientIntake.substanceUse}</p></div>}
                          {patientIntake.personalStrengths && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Strengths</p><p className="text-zinc-300">{patientIntake.personalStrengths}</p></div>}
                          {patientIntake.supportPeople && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Support Network</p><p className="text-zinc-300">{patientIntake.supportPeople}</p></div>}
                        </div>
                      </div>
                    )}

                    {/* Therapy Goals */}
                    {patientIntake.whatWouldBeDifferent && (
                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Therapy Goals</h4>
                        <p className="text-sm text-zinc-300 leading-relaxed">{patientIntake.whatWouldBeDifferent}</p>
                      </div>
                    )}
                  </div>

'''

# Replace lines start through end-1 with new content
new_lines = lines[:start] + [new_overview] + lines[end:]

with open(filepath, 'w') as f:
    f.writelines(new_lines)

print(f"Replaced overview (lines {start+1}-{end}) with enhanced version")
