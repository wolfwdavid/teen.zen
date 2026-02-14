import sys

filepath = sys.argv[1] if len(sys.argv) > 1 else 'src/App.jsx'

with open(filepath, 'r') as f:
    lines = f.readlines()

content = ''.join(lines)
changes = 0

# 1. Add Maximize2, Minimize2 to imports (only if not already there)
if 'Maximize2' not in content:
    content = content.replace(
        'ChevronLeft, ChevronRight, Archive, Search, Hash, Lock',
        'ChevronLeft, ChevronRight, Archive, Search, Hash, Lock, Maximize2, Minimize2',
        1
    )
    changes += 1
    print("[1] Added Maximize2, Minimize2 imports")

# 2. Add state variables (find the line with showMobileGraph and insert after)
if 'graphPanelWidth' not in content:
    content = content.replace(
        'const [showMobileGraph, setShowMobileGraph] = useState(false);',
        'const [showMobileGraph, setShowMobileGraph] = useState(false);\n  const [graphPanelWidth, setGraphPanelWidth] = useState(320);\n  const [graphCollapsed, setGraphCollapsed] = useState(false);',
        1
    )
    changes += 1
    print("[2] Added state variables")

# 3. Replace the panel - do it line by line for reliability
lines = content.split('\n')
new_lines = []
i = 0
replaced_panel = False
while i < len(lines):
    line = lines[i]
    # Find the panel start
    if not replaced_panel and '{/* RIGHT: Knowledge Graph Panel (desktop only) */}' in line:
        # Check next line has the old div
        if i + 1 < len(lines) and 'hidden md:flex w-[320px]' in lines[i + 1]:
            # Replace lines i through i+9 (the old header)
            new_lines.append('                    {/* RIGHT: Knowledge Graph Panel (desktop only) */}')
            new_lines.append('                    <div className={`hidden md:flex shrink-0 flex-col bg-zinc-950/30 overflow-hidden transition-all duration-300 relative ${graphCollapsed ? "w-[40px]" : ""}`} style={graphCollapsed ? {} : { width: graphPanelWidth }}>')
            new_lines.append('                      {graphCollapsed ? (')
            new_lines.append('                        <button onClick={() => setGraphCollapsed(false)} className="flex flex-col items-center justify-center h-full py-4 text-zinc-500 hover:text-indigo-400 transition-colors" title="Expand Knowledge Graph">')
            new_lines.append('                          <ChevronLeft size={14} />')
            new_lines.append('                          <span className="text-[9px] font-bold uppercase tracking-widest mt-2" style={{ writingMode: "vertical-rl" }}>Graph</span>')
            new_lines.append('                        </button>')
            new_lines.append('                      ) : (')
            new_lines.append('                        <>')
            new_lines.append('                      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800/50 shrink-0">')
            new_lines.append('                        <h4 className="text-[10px] font-bold uppercase tracking-widest text-indigo-400 flex items-center gap-1.5">')
            new_lines.append('                          <Globe size={12} /> Knowledge Graph')
            new_lines.append('                        </h4>')
            new_lines.append('                        <div className="flex items-center gap-2">')
            new_lines.append('                          <button onClick={() => setGraphPanelWidth(w => w === 320 ? 500 : 320)} className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors" title={graphPanelWidth === 320 ? "Expand" : "Shrink"}>')
            new_lines.append('                            {graphPanelWidth === 320 ? <Maximize2 size={10} /> : <Minimize2 size={10} />}')
            new_lines.append('                          </button>')
            new_lines.append('                          <button onClick={() => loadKnowledgeGraph(selectedPatient.id)} className="text-[10px] text-zinc-500 hover:text-zinc-300 flex items-center gap-1 transition-colors">')
            new_lines.append('                            <RefreshCw size={10} />')
            new_lines.append('                          </button>')
            new_lines.append('                          <button onClick={() => setGraphCollapsed(true)} className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors" title="Collapse">')
            new_lines.append('                            <ChevronRight size={12} />')
            new_lines.append('                          </button>')
            new_lines.append('                        </div>')
            new_lines.append('                      </div>')
            # Skip old lines: comment, div, div header, h4, Globe, /h4, button, className, RefreshCw, /button, /div
            # That's lines i through i+10
            i += 11
            replaced_panel = True
            changes += 1
            print("[3] Replaced Knowledge Graph panel header")
            continue
    new_lines.append(line)
    i += 1

content = '\n'.join(new_lines)

# 4. Close the fragment - find the closing pattern
# Look for:  )}  then  </div>  then  </div>  then  ) : activeChannel === 'tasks'
lines = content.split('\n')
new_lines = []
added_fragment_close = False
for i, line in enumerate(lines):
    new_lines.append(line)
    # After the last )} before </div></div> and activeChannel === 'tasks'
    if (not added_fragment_close 
        and line.strip() == ')}' 
        and i + 1 < len(lines) and lines[i + 1].strip() == '</div>'
        and i + 2 < len(lines) and lines[i + 2].strip() == '</div>'
        and i + 3 < len(lines) and "activeChannel === 'tasks'" in lines[i + 3]
        and '<>' in content):  # Only if we added the fragment opener
        new_lines.append('                        </>')
        new_lines.append('                      )}')
        added_fragment_close = True
        changes += 1
        print("[4] Added fragment close")

content = '\n'.join(new_lines)

# 5. Add useSuggestedPasswordReset
if 'useSuggestedPasswordReset' not in content:
    old = """  const useSuggestedPassword = () => {
    setRegForm({ ...regForm, password: suggestedPassword, confirmPassword: suggestedPassword });
  };"""
    new = """  const useSuggestedPassword = () => {
    setRegForm({ ...regForm, password: suggestedPassword, confirmPassword: suggestedPassword });
  };

  const useSuggestedPasswordReset = () => {
    setForgotNewPassword(suggestedPassword);
  };"""
    if old in content:
        content = content.replace(old, new, 1)
        changes += 1
        print("[5] Added useSuggestedPasswordReset")

# 6. Add password generator to reset form
if 'generateStrongPassword' not in content.split('forgotError')[0].split('New password')[1] if 'New password' in content else True:
    old = '''                        placeholder="New password (min 8 chars)" />
                      <button type="button" onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-400 transition-colors">
                        {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                  </div>
                  {forgotError && ('''
    new = '''                        placeholder="New password (min 8 chars)" />
                      <button type="button" onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-600 hover:text-zinc-400 transition-colors">
                        {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    </div>
                    <div className="flex items-center gap-2 mt-1.5 ml-1">
                      <button type="button" onClick={generateStrongPassword} className="text-[10px] text-indigo-400 hover:text-indigo-300 font-medium transition-colors">
                        Generate strong password
                      </button>
                      {suggestedPassword && (
                        <div className="flex items-center gap-2">
                          <code className="text-[10px] text-emerald-500/80 font-mono bg-zinc-900 px-2 py-0.5 rounded">{suggestedPassword}</code>
                          <button type="button" onClick={useSuggestedPasswordReset} className="text-[10px] text-indigo-400 hover:text-indigo-300 font-bold uppercase transition-colors">Use</button>
                        </div>
                      )}
                    </div>
                  </div>
                  {forgotError && ('''
    if old in content:
        content = content.replace(old, new, 1)
        changes += 1
        print("[6] Added password generator to reset form")

with open(filepath, 'w') as f:
    f.write(content)

print(f"\nDone! {changes} changes applied to {filepath}")