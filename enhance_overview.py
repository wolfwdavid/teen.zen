import sys

filepath = sys.argv[1] if len(sys.argv) > 1 else 'chatbot-rag/frontend/src/App.jsx'

with open(filepath, 'r') as f:
    content = f.read()

changes = 0

# Replace the overview card with enhanced version showing intake data
old_overview = """                ) : activeChannel === 'overview' ? (
                  /* ===== OVERVIEW ===== */
                  <div className="max-w-2xl space-y-6">
                    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">
                      <div className="flex items-center gap-4 mb-4">
                        <div className="h-16 w-16 rounded-2xl overflow-hidden bg-indigo-600/20 text-indigo-400 flex items-center justify-center text-2xl font-bold">
                          {selectedPatient.profile_pic
                            ? <img src={selectedPatient.profile_pic} alt="" className="h-full w-full object-cover" />
                            : capitalize(selectedPatient.username).charAt(0)
                          }
                        </div>
                        <div>
                          <h3 className="text-lg font-bold text-zinc-100">{capitalize(selectedPatient.username)}</h3>
                          <p className="text-sm text-zinc-500">{selectedPatient.email}</p>
                          {selectedPatient.age && <p className="text-xs text-zinc-600">Age: {selectedPatient.age}</p>}
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
                    {patientIntake.whatBringsYou && (
                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Quick Summary</h4>
                        <p className="text-sm text-zinc-300 leading-relaxed">{patientIntake.whatBringsYou}</p>
                      </div>
                    )}
                  </div>"""

new_overview = """                ) : activeChannel === 'overview' ? (
                  /* ===== OVERVIEW ===== */
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
                          <h3 className="text-lg font-bold text-zinc-100">{capitalize(selectedPatient.username)}</h3>
                          <p className="text-sm text-zinc-500">{selectedPatient.email}</p>
                          <div className="flex items-center gap-3 mt-1">
                            {selectedPatient.age && <p className="text-xs text-zinc-600">Age: {selectedPatient.age}</p>}
                            {patientIntake.pronouns && <p className="text-xs text-zinc-600">{patientIntake.pronouns}</p>}
                            {patientIntake.dateOfBirth && <p className="text-xs text-zinc-600">DOB: {patientIntake.dateOfBirth}</p>}
                          </div>
                          {patientIntake.phone && <p className="text-xs text-zinc-600 mt-0.5">Phone: {patientIntake.phone}</p>}
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

                    {/* Quick Summary */}
                    {patientIntake.whatBringsYou && (
                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Presenting Concern</h4>
                        <p className="text-sm text-zinc-300 leading-relaxed">{patientIntake.whatBringsYou}</p>
                        {patientIntake.whyNow && <p className="text-sm text-zinc-400 mt-2 italic">Why now: {patientIntake.whyNow}</p>}
                      </div>
                    )}

                    {/* Risk & Safety Snapshot */}
                    {(patientIntake.thoughtsHarmSelf || patientIntake.thoughtsHarmOthers || patientIntake.selfHarmHistory) && (
                      <div className="rounded-2xl border border-red-900/30 bg-red-950/20 p-6">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-red-400 mb-3">Risk & Safety</h4>
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          {patientIntake.thoughtsHarmSelf && (
                            <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Self-Harm Thoughts</p><p className="text-zinc-300">{patientIntake.thoughtsHarmSelf}</p></div>
                          )}
                          {patientIntake.thoughtsHarmOthers && (
                            <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Harm to Others</p><p className="text-zinc-300">{patientIntake.thoughtsHarmOthers}</p></div>
                          )}
                          {patientIntake.selfHarmHistory && (
                            <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Self-Harm History</p><p className="text-zinc-300">{patientIntake.selfHarmHistory}</p></div>
                          )}
                          {patientIntake.currentPlans && (
                            <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Current Plans</p><p className="text-zinc-300">{patientIntake.currentPlans}</p></div>
                          )}
                          {patientIntake.accessToMeans && (
                            <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Access to Means</p><p className="text-zinc-300">{patientIntake.accessToMeans}</p></div>
                          )}
                          {patientIntake.protectiveFactors && (
                            <div className="col-span-2"><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Protective Factors</p><p className="text-zinc-300">{patientIntake.protectiveFactors}</p></div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Clinical Snapshot */}
                    {(patientIntake.medications || patientIntake.pastDiagnoses || patientIntake.previousTherapy) && (
                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Clinical History</h4>
                        <div className="space-y-3 text-xs">
                          {patientIntake.pastDiagnoses && (
                            <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Past Diagnoses</p><p className="text-zinc-300">{patientIntake.pastDiagnoses}</p></div>
                          )}
                          {patientIntake.medications && (
                            <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Medications</p><p className="text-zinc-300">{patientIntake.medications}</p></div>
                          )}
                          {patientIntake.previousTherapy && (
                            <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Previous Therapy</p><p className="text-zinc-300">{patientIntake.previousTherapy}</p></div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Life Context */}
                    {(patientIntake.occupation || patientIntake.livingSituation || patientIntake.romanticStatus) && (
                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Life Context</h4>
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          {patientIntake.occupation && (
                            <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Occupation</p><p className="text-zinc-300">{patientIntake.occupation}</p></div>
                          )}
                          {patientIntake.romanticStatus && (
                            <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Relationship</p><p className="text-zinc-300">{patientIntake.romanticStatus}</p></div>
                          )}
                          {patientIntake.livingSituation && (
                            <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Living Situation</p><p className="text-zinc-300">{patientIntake.livingSituation}</p></div>
                          )}
                          {patientIntake.safetyAtHome && (
                            <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Safety at Home</p><p className="text-zinc-300">{patientIntake.safetyAtHome}</p></div>
                          )}
                          {patientIntake.familyDynamics && (
                            <div className="col-span-2"><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Family Dynamics</p><p className="text-zinc-300">{patientIntake.familyDynamics}</p></div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Coping & Strengths */}
                    {(patientIntake.copingWhenStressed || patientIntake.personalStrengths || patientIntake.substanceUse) && (
                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Coping & Strengths</h4>
                        <div className="space-y-3 text-xs">
                          {patientIntake.copingWhenStressed && (
                            <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Coping When Stressed</p><p className="text-zinc-300">{patientIntake.copingWhenStressed}</p></div>
                          )}
                          {patientIntake.substanceUse && (
                            <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Substance Use</p><p className="text-zinc-300">{patientIntake.substanceUse}</p></div>
                          )}
                          {patientIntake.personalStrengths && (
                            <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Strengths</p><p className="text-zinc-300">{patientIntake.personalStrengths}</p></div>
                          )}
                          {patientIntake.supportPeople && (
                            <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Support Network</p><p className="text-zinc-300">{patientIntake.supportPeople}</p></div>
                          )}
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
                  </div>"""

if old_overview in content:
    content = content.replace(old_overview, new_overview, 1)
    changes += 1
    print("[1] Enhanced overview card with intake data sections")
else:
    print("[1] SKIP - could not find overview block")

with open(filepath, 'w') as f:
    f.write(content)

print(f"\nDone! {changes} changes applied to {filepath}")
