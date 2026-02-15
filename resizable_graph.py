filepath = 'chatbot-rag/frontend/src/App.jsx'

with open(filepath, 'r') as f:
    content = f.read()

changes = 0

# 1. Add state variables after showMobileGraph state
old_state = "const [showMobileGraph, setShowMobileGraph] = useState(false);"
new_state = """const [showMobileGraph, setShowMobileGraph] = useState(false);
  const [graphPanelWidth, setGraphPanelWidth] = useState(320);
  const [graphCollapsed, setGraphCollapsed] = useState(false);
  const graphResizing = useRef(false);"""

if old_state in content and 'graphPanelWidth' not in content:
    content = content.replace(old_state, new_state, 1)
    changes += 1
    print("[1] Added graph panel state variables")

# 2. Add resize handler function - find a good spot before the return statement
# Add after the state declarations, before the first useEffect or function
old_handler_spot = "  const handleSendMessage = async (e) => {"
resize_handler = """  // Knowledge Graph resize handler
  const handleGraphResize = (e) => {
    e.preventDefault();
    graphResizing.current = true;
    const startX = e.clientX;
    const startWidth = graphPanelWidth;
    const onMouseMove = (ev) => {
      const delta = startX - ev.clientX;
      const newWidth = Math.min(600, Math.max(200, startWidth + delta));
      setGraphPanelWidth(newWidth);
    };
    const onMouseUp = () => {
      graphResizing.current = false;
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  };

  const handleSendMessage = async (e) => {"""

if 'handleGraphResize' not in content:
    content = content.replace(old_handler_spot, resize_handler, 1)
    changes += 1
    print("[2] Added resize handler function")

# 3. Replace the static panel with collapsible/resizable version
old_panel = '                    {/* RIGHT: Knowledge Graph Panel (desktop only) */}\n                    <div className="hidden md:flex w-[320px] shrink-0 flex-col bg-zinc-950/30 overflow-hidden">'

new_panel = """                    {/* RIGHT: Knowledge Graph Panel (desktop only) */}
                    {/* Resize handle */}
                    {!graphCollapsed && (
                      <div onMouseDown={handleGraphResize}
                        className="hidden md:flex w-1.5 shrink-0 cursor-col-resize items-center justify-center hover:bg-indigo-500/30 active:bg-indigo-500/50 transition-colors group"
                        title="Drag to resize">
                        <div className="w-0.5 h-8 rounded-full bg-zinc-700 group-hover:bg-indigo-400 transition-colors" />
                      </div>
                    )}
                    {graphCollapsed ? (
                      <div className="hidden md:flex w-10 shrink-0 flex-col items-center bg-zinc-950/30 border-l border-zinc-800/50 cursor-pointer hover:bg-zinc-900/50 transition-colors"
                        onClick={() => setGraphCollapsed(false)} title="Expand Knowledge Graph">
                        <div className="py-3 border-b border-zinc-800/50 w-full flex justify-center">
                          <ChevronLeft size={14} className="text-zinc-500" />
                        </div>
                        <div className="flex-1 flex items-center justify-center">
                          <span className="text-[10px] font-bold uppercase tracking-widest text-indigo-400/70 whitespace-nowrap" style={{writingMode: 'vertical-rl', transform: 'rotate(180deg)'}}>Graph</span>
                        </div>
                      </div>
                    ) : (
                    <div className="hidden md:flex shrink-0 flex-col bg-zinc-950/30 overflow-hidden transition-all duration-300" style={{width: graphPanelWidth + 'px'}}>"""

if old_panel in content:
    content = content.replace(old_panel, new_panel, 1)
    changes += 1
    print("[3] Replaced panel opening with collapsible/resizable version")

# 4. Add collapse button to the header
old_header = """                        <button onClick={() => loadKnowledgeGraph(selectedPatient.id)}
                          className="text-[10px] text-zinc-500 hover:text-zinc-300 flex items-center gap-1 transition-colors">
                          <RefreshCw size={10} />
                        </button>
                      </div>"""

new_header = """                        <div className="flex items-center gap-1">
                          <button onClick={() => loadKnowledgeGraph(selectedPatient.id)}
                            className="text-[10px] text-zinc-500 hover:text-zinc-300 flex items-center gap-1 transition-colors" title="Refresh">
                            <RefreshCw size={10} />
                          </button>
                          <button onClick={() => setGraphCollapsed(true)}
                            className="text-zinc-500 hover:text-zinc-300 transition-colors" title="Collapse panel">
                            <ChevronRight size={14} />
                          </button>
                        </div>
                      </div>"""

if old_header in content:
    content = content.replace(old_header, new_header, 1)
    changes += 1
    print("[4] Added collapse button to header")

# 5. Close the extra ternary - find the closing </div> of the graph panel
# The panel ends with:  </div>\n                  </div>  before ) : activeChannel === 'tasks'
old_close = """                    </div>
                  </div>

                ) : activeChannel === 'tasks' ? ("""

new_close = """                    </div>
                    )}
                  </div>

                ) : activeChannel === 'tasks' ? ("""

if old_close in content:
    content = content.replace(old_close, new_close, 1)
    changes += 1
    print("[5] Added closing bracket for ternary")

with open(filepath, 'w') as f:
    f.write(content)

print(f"\nDone! {changes} changes applied")
