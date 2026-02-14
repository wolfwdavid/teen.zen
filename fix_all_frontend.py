import sys, re

filepath = 'chatbot-rag/frontend/src/App.jsx'

with open(filepath, 'r') as f:
    lines = f.readlines()

new_lines = []
i = 0
changes = 0

while i < len(lines):
    line = lines[i]

    # FIX 1: Replace saveProfileData (lines ~408-414)
    if line.strip() == 'const saveProfileData = () => {':
        # Skip old function (through closing };)
        j = i + 1
        brace_count = 1
        while j < len(lines) and brace_count > 0:
            if '{' in lines[j]: brace_count += lines[j].count('{')
            if '}' in lines[j]: brace_count -= lines[j].count('}')
            j += 1
        # Write new function
        new_lines.append('  const saveProfileData = async () => {\n')
        new_lines.append('    try {\n')
        new_lines.append('      window.localStorage?.setItem(`profileData_${currentUser.id}`, JSON.stringify(profileData));\n')
        new_lines.append('      if (authToken) {\n')
        new_lines.append("        await fetch(joinUrl(API_BASE, '/api/profile/data'), {\n")
        new_lines.append("          method: 'POST',\n")
        new_lines.append("          headers: { ...authHeaders(authToken), 'Content-Type': 'application/json' },\n")
        new_lines.append('          body: JSON.stringify({ profile_data: profileData })\n')
        new_lines.append('        });\n')
        new_lines.append('      }\n')
        new_lines.append('      setProfileSaved(true);\n')
        new_lines.append('      setTimeout(() => setProfileSaved(false), 2000);\n')
        new_lines.append('    } catch {}\n')
        new_lines.append('  };\n')
        i = j
        changes += 1
        print(f"[1] Fixed saveProfileData at line {i} + added backend sync")
        continue

    # FIX 2: Fix localStorage getItem backtick syntax
    if 'getItem`profileData_' in line:
        line = line.replace('getItem`profileData_', 'getItem(`profileData_')
        # also fix the closing - find the backtick that closes the template
        line = line.replace('}`)', '}`)')  # already correct if closing with )
        changes += 1
        print(f"[2] Fixed getItem backtick at line {i+1}")

    # FIX 3: Replace overview card section
    if "activeChannel === 'overview'" in line and '?' in line and 'activeChannel' in lines[i-1] if i > 0 else False:
        # Find the end of the overview section (next activeChannel check)
        j = i + 1
        while j < len(lines):
            if "activeChannel === 'presenting'" in lines[j] or "activeChannel === 'present'" in lines[j]:
                break
            j += 1
        # j now points to the line with the next section
        # Go back to find the closing ) : before it
        end = j
        while end > i and ') :' not in lines[end] and ')  :' not in lines[end]:
            end -= 1

        # Write the new overview
        new_lines.append(line)  # keep the ternary line
        new_lines.append('                  /* ===== OVERVIEW ===== */\n')
        new_lines.append('                  <div className="max-w-2xl space-y-6">\n')
        new_lines.append('                    {/* Profile Card */}\n')
        new_lines.append('                    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">\n')
        new_lines.append('                      <div className="flex items-center gap-4 mb-4">\n')
        new_lines.append('                        <div className="h-16 w-16 rounded-2xl overflow-hidden bg-indigo-600/20 text-indigo-400 flex items-center justify-center text-2xl font-bold">\n')
        new_lines.append('                          {selectedPatient.profile_pic\n')
        new_lines.append('                            ? <img src={selectedPatient.profile_pic} alt="" className="h-full w-full object-cover" />\n')
        new_lines.append('                            : capitalize(selectedPatient.username).charAt(0)\n')
        new_lines.append('                          }\n')
        new_lines.append('                        </div>\n')
        new_lines.append('                        <div>\n')
        new_lines.append('                          <h3 className="text-lg font-bold text-zinc-100">{patientProfileData.fullName || capitalize(selectedPatient.username)}</h3>\n')
        new_lines.append('                          <p className="text-sm text-zinc-500">{selectedPatient.email}</p>\n')
        new_lines.append('                          <div className="flex items-center gap-3 mt-1 flex-wrap">\n')
        new_lines.append('                            {patientProfileData.pronouns && <span className="text-xs text-indigo-400/70 bg-indigo-500/10 px-2 py-0.5 rounded-full">{patientProfileData.pronouns}</span>}\n')
        new_lines.append('                            {patientProfileData.dob && <p className="text-xs text-zinc-500">DOB: {patientProfileData.dob}</p>}\n')
        new_lines.append('                            {selectedPatient.age && <p className="text-xs text-zinc-500">Age: {selectedPatient.age}</p>}\n')
        new_lines.append('                          </div>\n')
        new_lines.append('                          {(patientProfileData.contactPhone || patientProfileData.contactEmail) && (\n')
        new_lines.append('                            <div className="flex items-center gap-3 mt-1">\n')
        new_lines.append('                              {patientProfileData.contactPhone && <p className="text-xs text-zinc-500">Phone: {patientProfileData.contactPhone}</p>}\n')
        new_lines.append('                              {patientProfileData.contactEmail && <p className="text-xs text-zinc-500">Email: {patientProfileData.contactEmail}</p>}\n')
        new_lines.append('                            </div>\n')
        new_lines.append('                          )}\n')
        new_lines.append('                          {patientProfileData.preferredName && <p className="text-xs text-zinc-600 mt-0.5">Goes by: {patientProfileData.preferredName}</p>}\n')
        new_lines.append('                        </div>\n')
        new_lines.append('                      </div>\n')
        new_lines.append('                      <div className="grid grid-cols-2 gap-4 text-xs">\n')
        new_lines.append('                        <div className="rounded-xl bg-zinc-950/50 p-3 border border-zinc-800">\n')
        new_lines.append('                          <p className="text-zinc-500 text-[10px] uppercase tracking-widest font-bold mb-1">Joined</p>\n')
        new_lines.append("                          <p className=\"text-zinc-300\">{selectedPatient.created_at ? new Date(selectedPatient.created_at).toLocaleDateString() : 'N/A'}</p>\n")
        new_lines.append('                        </div>\n')
        new_lines.append('                        <div className="rounded-xl bg-zinc-950/50 p-3 border border-zinc-800">\n')
        new_lines.append('                          <p className="text-zinc-500 text-[10px] uppercase tracking-widest font-bold mb-1">Last Active</p>\n')
        new_lines.append("                          <p className=\"text-zinc-300\">{selectedPatient.last_login ? new Date(selectedPatient.last_login).toLocaleDateString() : 'N/A'}</p>\n")
        new_lines.append('                        </div>\n')
        new_lines.append('                        <div className="rounded-xl bg-zinc-950/50 p-3 border border-zinc-800">\n')
        new_lines.append('                          <p className="text-zinc-500 text-[10px] uppercase tracking-widest font-bold mb-1">Distress Level</p>\n')
        new_lines.append("                          <p className=\"text-zinc-300 font-mono\">{patientIntake.distressLevel ?? '\\u2014'} / 10</p>\n")
        new_lines.append('                        </div>\n')
        new_lines.append('                        <div className="rounded-xl bg-zinc-950/50 p-3 border border-zinc-800">\n')
        new_lines.append('                          <p className="text-zinc-500 text-[10px] uppercase tracking-widest font-bold mb-1">Assigned</p>\n')
        new_lines.append("                          <p className=\"text-zinc-300\">{selectedPatient.assigned_at ? new Date(selectedPatient.assigned_at).toLocaleDateString() : 'N/A'}</p>\n")
        new_lines.append('                        </div>\n')
        new_lines.append('                      </div>\n')
        new_lines.append('                    </div>\n')
        new_lines.append('\n')
        # Emergency Contact
        new_lines.append('                    {/* Emergency Contact */}\n')
        new_lines.append('                    {(patientProfileData.emergencyName || patientProfileData.emergencyPhone) && (\n')
        new_lines.append('                      <div className="rounded-2xl border border-amber-900/30 bg-amber-950/20 p-6">\n')
        new_lines.append('                        <h4 className="text-xs font-bold uppercase tracking-widest text-amber-400 mb-3">Emergency Contact</h4>\n')
        new_lines.append('                        <div className="grid grid-cols-3 gap-3 text-xs">\n')
        new_lines.append('                          {patientProfileData.emergencyName && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Name</p><p className="text-zinc-300">{patientProfileData.emergencyName}</p></div>}\n')
        new_lines.append('                          {patientProfileData.emergencyRelation && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Relationship</p><p className="text-zinc-300">{patientProfileData.emergencyRelation}</p></div>}\n')
        new_lines.append('                          {patientProfileData.emergencyPhone && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Phone</p><p className="text-zinc-300">{patientProfileData.emergencyPhone}</p></div>}\n')
        new_lines.append('                        </div>\n')
        new_lines.append('                      </div>\n')
        new_lines.append('                    )}\n')
        new_lines.append('\n')
        # Parent / Guardian
        new_lines.append('                    {/* Parent / Guardian */}\n')
        new_lines.append('                    {patientProfileData.parent1FullName && (\n')
        new_lines.append('                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">\n')
        new_lines.append('                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Parent / Guardian</h4>\n')
        new_lines.append('                        <div className="space-y-4">\n')
        new_lines.append('                          <div>\n')
        new_lines.append('                            <p className="text-xs text-zinc-400 font-semibold mb-2">Guardian 1</p>\n')
        new_lines.append('                            <div className="grid grid-cols-2 gap-3 text-xs">\n')
        new_lines.append("                              <div><p className=\"text-zinc-500 text-[10px] uppercase font-bold mb-0.5\">Name</p><p className=\"text-zinc-300\">{patientProfileData.parent1FullName}{patientProfileData.parent1PreferredName ? ` (${patientProfileData.parent1PreferredName})` : ''}</p></div>\n")
        new_lines.append('                              {patientProfileData.parent1Pronouns && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Pronouns</p><p className="text-zinc-300">{patientProfileData.parent1Pronouns}</p></div>}\n')
        new_lines.append('                              {patientProfileData.parent1ContactPhone && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Phone</p><p className="text-zinc-300">{patientProfileData.parent1ContactPhone}</p></div>}\n')
        new_lines.append('                              {patientProfileData.parent1ContactEmail && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Email</p><p className="text-zinc-300">{patientProfileData.parent1ContactEmail}</p></div>}\n')
        new_lines.append('                            </div>\n')
        new_lines.append('                          </div>\n')
        new_lines.append('                          {patientProfileData.parent2FullName && (\n')
        new_lines.append('                            <div>\n')
        new_lines.append('                              <p className="text-xs text-zinc-400 font-semibold mb-2">Guardian 2</p>\n')
        new_lines.append('                              <div className="grid grid-cols-2 gap-3 text-xs">\n')
        new_lines.append("                                <div><p className=\"text-zinc-500 text-[10px] uppercase font-bold mb-0.5\">Name</p><p className=\"text-zinc-300\">{patientProfileData.parent2FullName}{patientProfileData.parent2PreferredName ? ` (${patientProfileData.parent2PreferredName})` : ''}</p></div>\n")
        new_lines.append('                                {patientProfileData.parent2Pronouns && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Pronouns</p><p className="text-zinc-300">{patientProfileData.parent2Pronouns}</p></div>}\n')
        new_lines.append('                                {patientProfileData.parent2ContactPhone && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Phone</p><p className="text-zinc-300">{patientProfileData.parent2ContactPhone}</p></div>}\n')
        new_lines.append('                                {patientProfileData.parent2ContactEmail && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Email</p><p className="text-zinc-300">{patientProfileData.parent2ContactEmail}</p></div>}\n')
        new_lines.append('                              </div>\n')
        new_lines.append('                            </div>\n')
        new_lines.append('                          )}\n')
        new_lines.append('                        </div>\n')
        new_lines.append('                      </div>\n')
        new_lines.append('                    )}\n')
        new_lines.append('\n')
        # Consent & Logistics
        new_lines.append('                    {/* Consent & Logistics */}\n')
        new_lines.append('                    {(patientProfileData.sessionFormat || patientProfileData.paymentInfo || patientProfileData.consentAcknowledged) && (\n')
        new_lines.append('                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">\n')
        new_lines.append('                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Consent & Logistics</h4>\n')
        new_lines.append('                        <div className="grid grid-cols-2 gap-3 text-xs">\n')
        new_lines.append('                          <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Informed Consent</p><p className={patientProfileData.consentAcknowledged ? "text-emerald-400" : "text-red-400"}>{patientProfileData.consentAcknowledged ? "Acknowledged" : "Not yet"}</p></div>\n')
        new_lines.append('                          <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Confidentiality</p><p className={patientProfileData.confidentialityExplained ? "text-emerald-400" : "text-red-400"}>{patientProfileData.confidentialityExplained ? "Explained" : "Not yet"}</p></div>\n')
        new_lines.append('                          {patientProfileData.sessionFormat && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Session Format</p><p className="text-zinc-300">{patientProfileData.sessionFormat}</p></div>}\n')
        new_lines.append('                          {patientProfileData.paymentInfo && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Payment / Insurance</p><p className="text-zinc-300">{patientProfileData.paymentInfo}</p></div>}\n')
        new_lines.append('                        </div>\n')
        new_lines.append('                      </div>\n')
        new_lines.append('                    )}\n')
        new_lines.append('\n')
        # Presenting Concern
        new_lines.append('                    {/* Presenting Concern */}\n')
        new_lines.append('                    {patientIntake.whatBringsYou && (\n')
        new_lines.append('                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">\n')
        new_lines.append('                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Presenting Concern</h4>\n')
        new_lines.append('                        <p className="text-sm text-zinc-300 leading-relaxed">{patientIntake.whatBringsYou}</p>\n')
        new_lines.append('                        {patientIntake.whyNow && <p className="text-sm text-zinc-400 mt-2 italic">Why now: {patientIntake.whyNow}</p>}\n')
        new_lines.append('                      </div>\n')
        new_lines.append('                    )}\n')
        new_lines.append('\n')
        # Risk & Safety
        new_lines.append('                    {/* Risk & Safety */}\n')
        new_lines.append('                    {(patientIntake.thoughtsHarmSelf || patientIntake.thoughtsHarmOthers || patientIntake.selfHarmHistory) && (\n')
        new_lines.append('                      <div className="rounded-2xl border border-red-900/30 bg-red-950/20 p-6">\n')
        new_lines.append('                        <h4 className="text-xs font-bold uppercase tracking-widest text-red-400 mb-3">Risk & Safety</h4>\n')
        new_lines.append('                        <div className="grid grid-cols-2 gap-3 text-xs">\n')
        new_lines.append('                          {patientIntake.thoughtsHarmSelf && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Self-Harm Thoughts</p><p className="text-zinc-300">{patientIntake.thoughtsHarmSelf}</p></div>}\n')
        new_lines.append('                          {patientIntake.thoughtsHarmOthers && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Harm to Others</p><p className="text-zinc-300">{patientIntake.thoughtsHarmOthers}</p></div>}\n')
        new_lines.append('                          {patientIntake.selfHarmHistory && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Self-Harm History</p><p className="text-zinc-300">{patientIntake.selfHarmHistory}</p></div>}\n')
        new_lines.append('                          {patientIntake.currentPlans && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Current Plans</p><p className="text-zinc-300">{patientIntake.currentPlans}</p></div>}\n')
        new_lines.append('                          {patientIntake.protectiveFactors && <div className="col-span-2"><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Protective Factors</p><p className="text-zinc-300">{patientIntake.protectiveFactors}</p></div>}\n')
        new_lines.append('                        </div>\n')
        new_lines.append('                      </div>\n')
        new_lines.append('                    )}\n')
        new_lines.append('\n')
        # Clinical History
        new_lines.append('                    {/* Clinical History */}\n')
        new_lines.append('                    {(patientIntake.medications || patientIntake.pastDiagnoses || patientIntake.previousTherapy) && (\n')
        new_lines.append('                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">\n')
        new_lines.append('                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Clinical History</h4>\n')
        new_lines.append('                        <div className="space-y-3 text-xs">\n')
        new_lines.append('                          {patientIntake.pastDiagnoses && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Past Diagnoses</p><p className="text-zinc-300">{patientIntake.pastDiagnoses}</p></div>}\n')
        new_lines.append('                          {patientIntake.medications && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Medications</p><p className="text-zinc-300">{patientIntake.medications}</p></div>}\n')
        new_lines.append('                          {patientIntake.previousTherapy && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Previous Therapy</p><p className="text-zinc-300">{patientIntake.previousTherapy}</p></div>}\n')
        new_lines.append('                        </div>\n')
        new_lines.append('                      </div>\n')
        new_lines.append('                    )}\n')
        new_lines.append('\n')
        # Life Context
        new_lines.append('                    {/* Life Context */}\n')
        new_lines.append('                    {(patientIntake.occupation || patientIntake.livingSituation || patientIntake.romanticStatus) && (\n')
        new_lines.append('                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">\n')
        new_lines.append('                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Life Context</h4>\n')
        new_lines.append('                        <div className="grid grid-cols-2 gap-3 text-xs">\n')
        new_lines.append('                          {patientIntake.occupation && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Occupation</p><p className="text-zinc-300">{patientIntake.occupation}</p></div>}\n')
        new_lines.append('                          {patientIntake.romanticStatus && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Relationship</p><p className="text-zinc-300">{patientIntake.romanticStatus}</p></div>}\n')
        new_lines.append('                          {patientIntake.livingSituation && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Living Situation</p><p className="text-zinc-300">{patientIntake.livingSituation}</p></div>}\n')
        new_lines.append('                          {patientIntake.safetyAtHome && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Safety at Home</p><p className="text-zinc-300">{patientIntake.safetyAtHome}</p></div>}\n')
        new_lines.append('                          {patientIntake.familyDynamics && <div className="col-span-2"><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Family Dynamics</p><p className="text-zinc-300">{patientIntake.familyDynamics}</p></div>}\n')
        new_lines.append('                        </div>\n')
        new_lines.append('                      </div>\n')
        new_lines.append('                    )}\n')
        new_lines.append('\n')
        # Coping & Strengths
        new_lines.append('                    {/* Coping & Strengths */}\n')
        new_lines.append('                    {(patientIntake.copingWhenStressed || patientIntake.personalStrengths || patientIntake.substanceUse) && (\n')
        new_lines.append('                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">\n')
        new_lines.append('                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Coping & Strengths</h4>\n')
        new_lines.append('                        <div className="space-y-3 text-xs">\n')
        new_lines.append('                          {patientIntake.copingWhenStressed && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Coping When Stressed</p><p className="text-zinc-300">{patientIntake.copingWhenStressed}</p></div>}\n')
        new_lines.append('                          {patientIntake.substanceUse && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Substance Use</p><p className="text-zinc-300">{patientIntake.substanceUse}</p></div>}\n')
        new_lines.append('                          {patientIntake.personalStrengths && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Strengths</p><p className="text-zinc-300">{patientIntake.personalStrengths}</p></div>}\n')
        new_lines.append('                          {patientIntake.supportPeople && <div><p className="text-zinc-500 text-[10px] uppercase font-bold mb-0.5">Support Network</p><p className="text-zinc-300">{patientIntake.supportPeople}</p></div>}\n')
        new_lines.append('                        </div>\n')
        new_lines.append('                      </div>\n')
        new_lines.append('                    )}\n')
        new_lines.append('\n')
        # Therapy Goals
        new_lines.append('                    {/* Therapy Goals */}\n')
        new_lines.append('                    {patientIntake.whatWouldBeDifferent && (\n')
        new_lines.append('                      <div className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-6">\n')
        new_lines.append('                        <h4 className="text-xs font-bold uppercase tracking-widest text-indigo-400 mb-3">Therapy Goals</h4>\n')
        new_lines.append('                        <p className="text-sm text-zinc-300 leading-relaxed">{patientIntake.whatWouldBeDifferent}</p>\n')
        new_lines.append('                      </div>\n')
        new_lines.append('                    )}\n')
        new_lines.append('                  </div>\n')
        new_lines.append('\n')

        # Skip to the next section
        i = end
        changes += 1
        print(f"[3] Replaced overview with enhanced version (ended at line {end})")
        continue

    new_lines.append(line)
    i += 1

with open(filepath, 'w') as f:
    f.writelines(new_lines)

print(f"\nDone! {changes} changes applied")
