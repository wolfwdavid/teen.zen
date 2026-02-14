filepath = 'chatbot-rag/frontend/src/App.jsx'

with open(filepath, 'r') as f:
    lines = f.readlines()

new_lines = []
changes = 0

i = 0
while i < len(lines):
    line = lines[i]

    # 1. Add file upload state after existing input state
    if 'const [input, setInput] = useState' in line and 'uploadedFile' not in ''.join(lines[i:i+5]):
        new_lines.append(line)
        new_lines.append('  const [uploadedFile, setUploadedFile] = useState(null);\n')
        new_lines.append('  const [uploadedFileText, setUploadedFileText] = useState("");\n')
        new_lines.append('  const fileInputRef = useRef(null);\n')
        i += 1
        changes += 1
        print("[1] Added file upload state")
        continue

    # 2. Add file handler function before handleSendMessage
    if 'const handleSendMessage = async (e) => {' in line and 'handleFileUpload' not in ''.join(lines[max(0,i-20):i]):
        new_lines.append('  const handleFileUpload = async (e) => {\n')
        new_lines.append('    const file = e.target.files[0];\n')
        new_lines.append('    if (!file) return;\n')
        new_lines.append('    setUploadedFile(file);\n')
        new_lines.append('    try {\n')
        new_lines.append('      if (file.type === "text/plain" || file.name.endsWith(".txt") || file.name.endsWith(".md") || file.name.endsWith(".csv")) {\n')
        new_lines.append('        const text = await file.text();\n')
        new_lines.append('        setUploadedFileText(text.slice(0, 3000));\n')
        new_lines.append('      } else if (file.type === "application/json" || file.name.endsWith(".json")) {\n')
        new_lines.append('        const text = await file.text();\n')
        new_lines.append('        setUploadedFileText(text.slice(0, 3000));\n')
        new_lines.append('      } else {\n')
        new_lines.append('        setUploadedFileText("[File: " + file.name + " (" + (file.size / 1024).toFixed(1) + " KB) - binary file, content not readable]");\n')
        new_lines.append('      }\n')
        new_lines.append('    } catch { setUploadedFileText("[Could not read file]"); }\n')
        new_lines.append('    e.target.value = "";\n')
        new_lines.append('  };\n')
        new_lines.append('\n')
        changes += 1
        print("[2] Added handleFileUpload function")

    # 3. Modify the send to include file context
    if 'const userQuery = input.trim();' in line:
        new_lines.append('    let userQuery = input.trim();\n')
        new_lines.append('    if (uploadedFileText) {\n')
        new_lines.append('      userQuery = userQuery + "\\n\\n[Attached file: " + (uploadedFile?.name || "file") + "]\\n" + uploadedFileText;\n')
        new_lines.append('    }\n')
        i += 1
        # Also clear file after send - find setInput("") line
        while i < len(lines):
            if 'setInput("")' in lines[i]:
                new_lines.append(lines[i])
                new_lines.append('    setUploadedFile(null);\n')
                new_lines.append('    setUploadedFileText("");\n')
                i += 1
                changes += 1
                print("[3] Modified send to include file context")
                break
            new_lines.append(lines[i])
            i += 1
        continue

    # 4. Replace the chat <input> with <textarea> + file upload button
    if '<input type="text" value={input} onChange={(e) => setInput(e.target.value)} disabled={isLoading}' in line:
        # Skip the old input and its placeholder line
        j = i + 1
        while j < len(lines) and 'className="flex-1 bg-transparent' in lines[j]:
            j += 1
        
        # Write new textarea + file upload
        new_lines.append('                  <input type="file" ref={fileInputRef} onChange={handleFileUpload} className="hidden" accept=".txt,.md,.csv,.json,.pdf,.doc,.docx,.py,.js,.html,.css" />\n')
        new_lines.append('                  <button type="button" onClick={() => fileInputRef.current?.click()} className="flex h-10 w-10 items-center justify-center rounded-xl text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors" title="Upload file">\n')
        new_lines.append('                    <Paperclip size={18} />\n')
        new_lines.append('                  </button>\n')
        new_lines.append('                  <div className="flex-1 flex flex-col">\n')
        new_lines.append('                    {uploadedFile && (\n')
        new_lines.append('                      <div className="flex items-center gap-2 px-4 pt-2 pb-1">\n')
        new_lines.append('                        <span className="text-[10px] text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full">{uploadedFile.name}</span>\n')
        new_lines.append('                        <button type="button" onClick={() => { setUploadedFile(null); setUploadedFileText(""); }} className="text-zinc-500 hover:text-red-400"><X size={12} /></button>\n')
        new_lines.append('                      </div>\n')
        new_lines.append('                    )}\n')
        new_lines.append('                    <textarea value={input} onChange={(e) => setInput(e.target.value)} disabled={isLoading}\n')
        new_lines.append('                      onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (input.trim()) { handleSendMessage(e); } } }}\n')
        new_lines.append('                      placeholder={isLoading ? "Generating response..." : "Ask a question about your docs..."}\n')
        new_lines.append('                      rows={1}\n')
        new_lines.append('                      onInput={(e) => { e.target.style.height = "auto"; e.target.style.height = Math.min(e.target.scrollHeight, 150) + "px"; }}\n')
        new_lines.append('                      className="flex-1 bg-transparent px-4 py-3 text-sm outline-none placeholder:text-zinc-600 resize-none overflow-y-auto max-h-[150px]" />\n')
        new_lines.append('                  </div>\n')
        
        i = j
        changes += 1
        print("[4] Replaced input with textarea + file upload")
        continue

    # 5. Change form onSubmit to also handle Enter properly
    # (form already has onSubmit, textarea handles Enter via onKeyDown)

    new_lines.append(line)
    i += 1

# 6. Add Paperclip to lucide imports if not present
content = ''.join(new_lines)
if 'Paperclip' not in content:
    # Find the lucide import line
    content = content.replace(
        'ChevronLeft, ChevronRight, Archive, Search, Hash, Lock',
        'ChevronLeft, ChevronRight, Archive, Search, Hash, Lock, Paperclip',
        1
    )
    changes += 1
    print("[5] Added Paperclip import")

with open('chatbot-rag/frontend/src/App.jsx', 'w') as f:
    f.write(content)

print(f"\nDone! {changes} changes applied")
