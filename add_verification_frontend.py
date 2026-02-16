filepath = 'chatbot-rag/frontend/src/App.jsx'

with open(filepath, 'r') as f:
    content = f.read()

changes = 0

# 1. Add verification state after profileSaved state
old_saved = '  const [profileSaved, setProfileSaved] = useState(false);'
new_saved = '''  const [profileSaved, setProfileSaved] = useState(false);
  const [verificationStatus, setVerificationStatus] = useState('not_submitted');
  const [verificationRejection, setVerificationRejection] = useState('');
  const [verificationLoading, setVerificationLoading] = useState(false);
  const [idFile, setIdFile] = useState(null);
  const [videoBlob, setVideoBlob] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const mediaRecorderRef = useRef(null);
  const videoPreviewRef = useRef(null);
  const recordingTimerRef = useRef(null);
  const idFileInputRef = useRef(null);'''

if old_saved in content and 'verificationStatus' not in content:
    content = content.replace(old_saved, new_saved, 1)
    changes += 1
    print("[1] Added verification state")

# 2. Add verification functions before saveProfileData
old_save = '  const saveProfileData = async () => {'
new_functions = '''  // === VERIFICATION FUNCTIONS ===
  const loadVerificationStatus = async () => {
    if (!authToken) return;
    try {
      const res = await fetch(joinUrl(API_BASE, '/api/verification/status'), { headers: authHeaders(authToken) });
      if (res.ok) {
        const d = await res.json();
        setVerificationStatus(d.status || 'not_submitted');
        setVerificationRejection(d.rejection_reason || '');
      }
    } catch {}
  };

  const startVideoRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      if (videoPreviewRef.current) {
        videoPreviewRef.current.srcObject = stream;
        videoPreviewRef.current.play();
      }
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
      const chunks = [];
      mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'video/webm' });
        setVideoBlob(blob);
        stream.getTracks().forEach(t => t.stop());
        if (videoPreviewRef.current) videoPreviewRef.current.srcObject = null;
      };
      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start();
      setIsRecording(true);
      setRecordingTime(0);
      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(t => {
          if (t >= 20) { stopVideoRecording(); return 20; }
          return t + 1;
        });
      }, 1000);
    } catch (err) {
      alert('Camera access is required for video verification. Please allow camera access and try again.');
    }
  };

  const stopVideoRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
  };

  const submitVerification = async () => {
    if (!idFile && !videoBlob) { alert('Please upload an ID and record a video.'); return; }
    setVerificationLoading(true);
    try {
      const formData = new FormData();
      if (idFile) formData.append('id_document', idFile);
      if (videoBlob) formData.append('video', videoBlob, 'verification.webm');
      const res = await fetch(joinUrl(API_BASE, '/api/verification/upload'), {
        method: 'POST',
        headers: { 'Authorization': authToken },
        body: formData
      });
      if (res.ok) {
        setVerificationStatus('pending');
        setIdFile(null);
        setVideoBlob(null);
      }
    } catch (err) { alert('Upload failed. Please try again.'); }
    setVerificationLoading(false);
  };

  const saveProfileData = async () => {'''

if old_save in content and 'loadVerificationStatus' not in content:
    content = content.replace(old_save, new_functions, 1)
    changes += 1
    print("[2] Added verification functions")

# 3. Add loadVerificationStatus call to useEffect - find where profile loads
old_load = "loadVerificationStatus" 
# We need to call it on login. Find where tasks or profile data loads
# Add it right after the profile data load
if 'loadVerificationStatus();' not in content:
    # Find a good place to add the call - after loadTasks or similar
    old_tasks_call = "loadTasks();"
    if old_tasks_call in content:
        content = content.replace(old_tasks_call, "loadTasks();\n      loadVerificationStatus();", 1)
        changes += 1
        print("[3] Added loadVerificationStatus to startup")

# 4. Add verification section to user profile - after the consent section, before parent section
# Insert after the Campus section we just added
old_campus_end = '''              {/* ===== SECTION B: Parent/Guardian Information ===== */}'''
new_verification_section = '''              {/* ===== SECTION: Identity Verification ===== */}
              <div className="rounded-3xl border border-zinc-900 bg-zinc-900/30 p-8 backdrop-blur-xl ring-1 ring-white/5">
                <h3 className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-indigo-400 mb-6">
                  <ShieldCheck size={16} /> Identity Verification
                </h3>

                {verificationStatus === 'approved' ? (
                  <div className="flex items-center gap-3 rounded-xl bg-emerald-500/10 px-4 py-3 ring-1 ring-emerald-500/20">
                    <CheckCircle2 size={20} className="text-emerald-400" />
                    <div>
                      <p className="text-sm font-semibold text-emerald-400">Identity Verified</p>
                      <p className="text-xs text-zinc-400">Your identity has been confirmed by your therapist.</p>
                    </div>
                  </div>
                ) : verificationStatus === 'pending' ? (
                  <div className="flex items-center gap-3 rounded-xl bg-amber-500/10 px-4 py-3 ring-1 ring-amber-500/20">
                    <Clock size={20} className="text-amber-400" />
                    <div>
                      <p className="text-sm font-semibold text-amber-400">Verification Pending</p>
                      <p className="text-xs text-zinc-400">Your documents are being reviewed by your therapist.</p>
                    </div>
                  </div>
                ) : verificationStatus === 'rejected' ? (
                  <div className="space-y-4">
                    <div className="flex items-center gap-3 rounded-xl bg-red-500/10 px-4 py-3 ring-1 ring-red-500/20">
                      <ShieldAlert size={20} className="text-red-400" />
                      <div>
                        <p className="text-sm font-semibold text-red-400">Verification Rejected</p>
                        {verificationRejection && <p className="text-xs text-zinc-400">Reason: {verificationRejection}</p>}
                        <p className="text-xs text-zinc-500 mt-1">Please resubmit your documents below.</p>
                      </div>
                    </div>
                  </div>
                ) : null}

                {verificationStatus !== 'approved' && (
                  <div className="space-y-6 mt-4">
                    <p className="text-xs text-zinc-500">To verify your identity, please upload a valid ID (school ID, birth certificate, or government ID) and record a short 20-second video of yourself.</p>

                    {/* ID Upload */}
                    <div className="space-y-2">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Upload ID Document</label>
                      <input type="file" ref={idFileInputRef} onChange={(e) => setIdFile(e.target.files[0])} className="hidden" accept="image/*,.pdf" />
                      <div className="flex items-center gap-3">
                        <button onClick={() => idFileInputRef.current?.click()}
                          className="rounded-xl bg-zinc-800 px-4 py-2.5 text-xs text-zinc-300 hover:bg-zinc-700 transition-all flex items-center gap-2">
                          <Camera size={14} /> {idFile ? 'Change File' : 'Choose File'}
                        </button>
                        {idFile && <span className="text-xs text-indigo-400">{idFile.name}</span>}
                      </div>
                      <p className="text-[10px] text-zinc-600 ml-1">Accepted: Photo of ID, birth certificate, passport, or school ID</p>
                    </div>

                    {/* Video Recording */}
                    <div className="space-y-2">
                      <label className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 ml-1">Record 20-Second Video</label>
                      <div className="rounded-xl overflow-hidden bg-zinc-950 border border-zinc-800">
                        <video ref={videoPreviewRef} className="w-full h-48 object-cover bg-black" muted playsInline />
                        <div className="p-3 flex items-center justify-between">
                          {!isRecording && !videoBlob && (
                            <button onClick={startVideoRecording}
                              className="rounded-xl bg-red-600 px-4 py-2 text-xs text-white hover:bg-red-500 transition-all flex items-center gap-2">
                              <Circle size={12} className="fill-current" /> Start Recording
                            </button>
                          )}
                          {isRecording && (
                            <div className="flex items-center gap-3">
                              <button onClick={stopVideoRecording}
                                className="rounded-xl bg-red-600 px-4 py-2 text-xs text-white hover:bg-red-500 transition-all flex items-center gap-2 animate-pulse">
                                <StopCircle size={14} /> Stop ({20 - recordingTime}s)
                              </button>
                              <span className="text-xs text-red-400">Recording...</span>
                            </div>
                          )}
                          {videoBlob && !isRecording && (
                            <div className="flex items-center gap-3">
                              <span className="text-xs text-emerald-400">Video recorded</span>
                              <button onClick={() => { setVideoBlob(null); setRecordingTime(0); }}
                                className="text-xs text-zinc-500 hover:text-red-400 underline">Re-record</button>
                            </div>
                          )}
                        </div>
                      </div>
                      <p className="text-[10px] text-zinc-600 ml-1">Please look at the camera and state your name. Recording auto-stops at 20 seconds.</p>
                    </div>

                    {/* Submit */}
                    <button onClick={submitVerification} disabled={verificationLoading || (!idFile && !videoBlob)}
                      className={`w-full rounded-xl py-3 text-sm font-semibold transition-all flex items-center justify-center gap-2 ${
                        verificationLoading || (!idFile && !videoBlob)
                          ? 'bg-zinc-800 text-zinc-600 cursor-not-allowed'
                          : 'bg-indigo-600 text-white hover:bg-indigo-500 shadow-lg shadow-indigo-500/20'
                      }`}>
                      {verificationLoading ? <><Loader2 size={16} className="animate-spin" /> Uploading...</> : <><ShieldCheck size={16} /> Submit for Verification</>}
                    </button>
                  </div>
                )}
              </div>
              {/* ===== SECTION B: Parent/Guardian Information ===== */}'''

if old_campus_end in content and 'Identity Verification' not in content:
    content = content.replace(old_campus_end, new_verification_section, 1)
    changes += 1
    print("[4] Added verification section to user profile")

with open(filepath, 'w') as f:
    f.write(content)

print(f"\nDone! {changes} changes applied")
