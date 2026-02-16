filepath = 'chatbot-rag/frontend/src/App.jsx'

with open(filepath, 'r') as f:
    content = f.read()

changes = 0

# 1. Add new fields to profileData state defaults
old_state = "consentAcknowledged: false, confidentialityExplained: false,\n    sessionFormat: '', paymentInfo: ''"
new_state = "consentAcknowledged: false, confidentialityExplained: false,\n    sessionFormat: '', paymentInfo: '',\n    campusName: '', campusId: '', isFromOrphanage: false, orphanageName: ''"

if old_state in content:
    content = content.replace(old_state, new_state, 1)
    changes += 1
    print("[1] Added campus/orphanage to profileData state")

# 2. Add Campus & Living Situation section BEFORE the Parent/Guardian section in user profile
old_section_b = '              {/* ===== SECTION B: Parent/Guardian Information ===== */}'
new_campus_section = '''              {/* ===== SECTION: Campus & Living Situation ===== */}
              <div className="rounded-3xl border border-zinc-900 bg-zinc-900/30 p-8 backdrop-blur-xl ring-1 ring-white/5">
                <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-indigo-400 mb-6">
                  <Globe size={16} /> Campus & Living Situation
                </h3>
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">School / University / Campus</label>
                      <input value={profileData.campusName} onChange={(e) => updateProfile('campusName', e.target.value)}
                        className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                        placeholder="e.g. NYU, Lincoln High School" />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Student / Campus ID</label>
                      <input value={profileData.campusId} onChange={(e) => updateProfile('campusId', e.target.value)}
                        className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                        placeholder="Optional" />
                    </div>
                  </div>
                  <div className="border-t border-zinc-800/50 pt-4 mt-2">
                    <div className="flex items-center gap-3 mb-4">
                      <button onClick={() => updateProfile('isFromOrphanage', !profileData.isFromOrphanage)}
                        className={`shrink-0 w-5 h-5 rounded flex items-center justify-center border transition-all ${profileData.isFromOrphanage ? 'bg-indigo-600 border-indigo-500' : 'border-zinc-700'}`}>
                        {profileData.isFromOrphanage && <Check size={14} className="text-white" />}
                      </button>
                      <span className="text-sm text-zinc-300">I am from a children's home / orphanage</span>
                    </div>
                    {profileData.isFromOrphanage && (
                      <div className="space-y-1 ml-8">
                        <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Name of Children's Home / Orphanage</label>
                        <input value={profileData.orphanageName} onChange={(e) => updateProfile('orphanageName', e.target.value)}
                          className="w-full rounded-xl border border-zinc-800 bg-zinc-950 px-4 py-3 text-sm focus:border-indigo-500/50 outline-none transition-all placeholder:text-zinc-700"
                          placeholder="Name of facility" />
                      </div>
                    )}
                  </div>
                </div>
              </div>
              {/* ===== SECTION B: Parent/Guardian Information ===== */}'''

if old_section_b in content:
    content = content.replace(old_section_b, new_campus_section, 1)
    changes += 1
    print("[2] Added Campus & Living Situation section to user profile")

# 3. Add campus/orphanage to provider overview - after the Consent & Logistics card
old_consent_end = '''                    {/* Presenting Concern */}'''
new_campus_overview = '''                    {/* Campus & Living Situation */}
                    {(patientProfileData.campusName || patientProfileData.orphanageName) && (
                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">
                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Campus & Living Situation</h4>
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          {patientProfileData.campusName && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Campus / School</p><p className="text-zinc-300">{patientProfileData.campusName}</p></div>}
                          {patientProfileData.campusId && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Student ID</p><p className="text-zinc-300">{patientProfileData.campusId}</p></div>}
                          {patientProfileData.orphanageName && <div className="col-span-2"><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Children\'s Home / Orphanage</p><p className="text-zinc-300">{patientProfileData.orphanageName}</p></div>}
                        </div>
                      </div>
                    )}

                    {/* Presenting Concern */}'''

if old_consent_end in content:
    content = content.replace(old_consent_end, new_campus_overview, 1)
    changes += 1
    print("[3] Added Campus & Living Situation to provider overview")

# 4. Add campus/orphanage to provider chat context
# This will be done in the backend script

with open(filepath, 'w') as f:
    f.write(content)

print(f"\nDone! {changes} changes applied")
