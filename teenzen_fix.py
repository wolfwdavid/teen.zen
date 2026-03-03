filepath = 'chatbot-rag/frontend/src/App.jsx'

with open(filepath, 'r') as f:
    content = f.read()

changes = 0

# 1. Add logo imports at top
if "import teenZenLogo" not in content:
    old = "import { useState, useEffect, useRef, useCallback } from 'react';"
    new = """import { useState, useEffect, useRef, useCallback } from 'react';
import teenZenLogo from './assets/teenzen-logo.png';
import teenZenLogoDark from './assets/teenzen-logo-dark.png';"""
    content = content.replace(old, new, 1)
    changes += 1
    print("[1] Added logo imports")

# 2. Add light/dark mode state after activeTab
if "darkMode" not in content:
    old = "const [activeTab, setActiveTab] = useState('home');"
    new = """const [activeTab, setActiveTab] = useState('home');
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('tz_darkMode');
    return saved !== null ? JSON.parse(saved) : true;
  });
  useEffect(() => { localStorage.setItem('tz_darkMode', JSON.stringify(darkMode)); }, [darkMode]);"""
    content = content.replace(old, new, 1)
    changes += 1
    print("[2] Added darkMode state")

# 3. Find the main return and add tab routing + bottom nav
# Strategy: Find where messages are rendered and wrap with tab logic
# First, let's find the chat messages area

lines = content.split('\n')

# Find the line with "How can I help you today?" to locate the chat area
chat_welcome_idx = None
for i, line in enumerate(lines):
    if 'How can I help you today?' in line:
        chat_welcome_idx = i
        break

if chat_welcome_idx:
    # Find the scrollable container above this (flex-1 overflow-y-auto)
    scroll_container_idx = None
    for i in range(chat_welcome_idx, max(chat_welcome_idx - 40, 0), -1):
        if 'overflow-y-auto' in lines[i] and 'flex-1' in lines[i]:
            scroll_container_idx = i
            break
    
    if scroll_container_idx:
        # Insert tab router BEFORE the scroll container
        indent = '              '
        tab_router = f"""{indent}{{/* === TAB ROUTER (authenticated teen users) === */}}
{indent}{{authToken && userRole !== 'provider' && activeTab === 'home' && renderHomeTab()}}
{indent}{{authToken && userRole !== 'provider' && activeTab === 'journal' && renderJournalTab()}}
{indent}{{authToken && userRole !== 'provider' && activeTab === 'progress' && renderProgressTab()}}
{indent}{{/* Show chat for: guests, providers, or when chat tab active */}}
{indent}{{((!authToken) || userRole === 'provider' || activeTab === 'chat') && ("""
        
        if 'TAB ROUTER' not in content:
            lines.insert(scroll_container_idx, tab_router)
            changes += 1
            print(f"[3] Added tab router at line {scroll_container_idx}")
            
            # Now find the end of the chat area (input bar area) and close the conditional
            # Find the input/textarea area after the messages
            # Look for the message input section
            for i in range(scroll_container_idx + 1, len(lines)):
                if '© 2026' in lines[i] or 'RAG-BOT' in lines[i]:
                    # Insert closing bracket before footer
                    lines.insert(i, f'{indent})}}\n')
                    changes += 1
                    print(f"[3b] Closed tab router conditional at line {i}")
                    break
            
            content = '\n'.join(lines)

# 4. Add bottom navigation bar before the footer
if 'Bottom Navigation' not in content:
    footer_marker = '© 2026'
    if footer_marker in content:
        # Find the footer line
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if footer_marker in line:
                # Go up to find the footer container div
                for j in range(i, max(i-5, 0), -1):
                    if '<div' in lines[j] and ('text-center' in lines[j] or 'footer' in lines[j].lower() or 'border-t' in lines[j]):
                        bottom_nav = """
            {/* ===== Bottom Navigation ===== */}
            {authToken && userRole !== 'provider' && (
              <div className="fixed bottom-0 left-0 right-0 z-50"
                style={{background: darkMode ? '#1a1a2e' : 'white', borderTop: darkMode ? '1px solid #2a2a4a' : '1px solid #E8ECF0'}}>
                <div className="flex items-center justify-around py-2 px-4 max-w-lg mx-auto">
                  {[
                    { id: 'home', icon: '🏠', label: 'Home' },
                    { id: 'chat', icon: '💬', label: 'Chat' },
                    { id: 'journal', icon: '📝', label: 'Journal' },
                    { id: 'progress', icon: '📊', label: 'Progress' },
                  ].map(tab => (
                    <button key={tab.id} onClick={() => { setActiveTab(tab.id); if(tab.id === 'chat') setView('chat'); }}
                      className="flex flex-col items-center gap-0.5 px-3 py-1 rounded-xl transition-all"
                      style={{color: activeTab === tab.id ? '#2EC4B6' : darkMode ? '#6B7C8F' : '#9CA8B5'}}>
                      <span className="text-xl">{tab.icon}</span>
                      <span className="text-[9px] font-semibold">{tab.label}</span>
                      {activeTab === tab.id && <div className="w-1 h-1 rounded-full mt-0.5" style={{background: '#2EC4B6'}} />}
                    </button>
                  ))}
                </div>
              </div>
            )}
"""
                        lines.insert(j, bottom_nav)
                        content = '\n'.join(lines)
                        changes += 1
                        print(f"[4] Added bottom navigation at line {j}")
                        break
                break

# 5. Add dark/light mode toggle button in the header
# Find the hamburger menu or header area
if 'darkMode toggle' not in content:
    # Find the header nav area - look for SIGN IN or CHAT button
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'DEBUG' in line and 'button' in line.lower() and 'onClick' in line:
            # Add dark mode toggle after debug button
            toggle_btn = """
                  {/* darkMode toggle */}
                  {authToken && (
                    <button onClick={() => setDarkMode(!darkMode)} className="px-3 py-2 rounded-xl text-sm transition-all"
                      style={{color: darkMode ? '#9CA8B5' : '#6B7C8F'}}>
                      {darkMode ? '☀️' : '🌙'}
                    </button>
                  )}"""
            # Insert after the debug line - find the closing of that button
            for k in range(i, min(i+3, len(lines))):
                if '</button>' in lines[k] or '/>' in lines[k]:
                    lines.insert(k+1, toggle_btn)
                    content = '\n'.join(lines)
                    changes += 1
                    print(f"[5] Added dark/light mode toggle in header")
                    break
            break

# 6. Update the main container background based on dark mode
# Find className="min-h-screen and add dynamic styling
if 'darkMode ?' not in content or content.count('darkMode ?') < 2:
    # Add a style prop to the outermost container
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'min-h-screen' in line and 'className' in line and i > 100:
            # Add style for dynamic background
            if 'style={{' not in line:
                lines[i] = line.replace('>', ' style={{background: darkMode ? "#0a0a1a" : "#F7F9FB", color: darkMode ? "#e0e0e0" : "#1F2933", transition: "background 0.3s, color 0.3s"}}>')
                changes += 1
                print(f"[6] Added dynamic background to main container at line {i}")
            break
    content = '\n'.join(lines)

# 7. Update the Home/Journal/Progress tabs to respect dark mode
# Replace hardcoded light colors in the tab renderers
if 'renderHomeTab' in content:
    # Update Home tab colors to use darkMode
    content = content.replace(
        "style={{color: '#1F2933'}}>\n          {(() => { const h = new Date().getHours()",
        "style={{color: darkMode ? '#e0e0e0' : '#1F2933'}}>\n          {(() => { const h = new Date().getHours()"
    )
    content = content.replace(
        "style={{color: '#6B7C8F'}}>How are you feeling today?",
        "style={{color: darkMode ? '#8896a4' : '#6B7C8F'}}>How are you feeling today?"
    )
    # Update card backgrounds in Home tab
    content = content.replace(
        "style={{background: 'white', border: '1px solid #E8ECF0'}}>\n        <h3 className=\"font-semibold mb-4 text-center\" style={{color: '#1F2933'}}>\n          {dailyMood",
        "style={{background: darkMode ? '#1a1a2e' : 'white', border: darkMode ? '1px solid #2a2a4a' : '1px solid #E8ECF0'}}>\n        <h3 className=\"font-semibold mb-4 text-center\" style={{color: darkMode ? '#e0e0e0' : '#1F2933'}}>\n          {dailyMood"
    )
    
    # Bulk replace remaining hardcoded colors in tab renderers
    # Cards
    old_card = "style={{background: 'white', border: '1px solid #E8ECF0'}}"
    new_card = "style={{background: darkMode ? '#1a1a2e' : 'white', border: darkMode ? '1px solid #2a2a4a' : '1px solid #E8ECF0'}}"
    content = content.replace(old_card, new_card)
    
    # Text primary
    old_text = "style={{color: '#1F2933'}}"
    new_text = "style={{color: darkMode ? '#e0e0e0' : '#1F2933'}}"
    content = content.replace(old_text, new_text)
    
    # Text secondary
    old_sub = "style={{color: '#6B7C8F'}}"
    new_sub = "style={{color: darkMode ? '#8896a4' : '#6B7C8F'}}"
    content = content.replace(old_sub, new_sub)
    
    # Text muted
    old_muted = "style={{color: '#9CA8B5'}}"
    new_muted = "style={{color: darkMode ? '#6B7C8F' : '#9CA8B5'}}"
    content = content.replace(old_muted, new_muted)
    
    # Input/textarea backgrounds
    old_input_bg = "style={{background: '#F7F9FB', color: '#1F2933', border: '1px solid #E8ECF0'}}"
    new_input_bg = "style={{background: darkMode ? '#0d0d1a' : '#F7F9FB', color: darkMode ? '#e0e0e0' : '#1F2933', border: darkMode ? '1px solid #2a2a4a' : '1px solid #E8ECF0'}}"
    content = content.replace(old_input_bg, new_input_bg)
    
    # Subtle backgrounds  
    old_subtle = "style={{background: '#F7F9FB'"
    new_subtle = "style={{background: darkMode ? '#0d0d1a' : '#F7F9FB'"
    content = content.replace(old_subtle, new_subtle)
    
    changes += 1
    print("[7] Updated tab renderers for dark/light mode")

# 8. Replace the welcome screen robot SVG icon
# Find the second SVG (welcome area) and replace
lines = content.split('\n')
svg_count = 0
for i, line in enumerate(lines):
    if '<svg' in line and ('viewBox' in line or 'xmlns' in line):
        svg_count += 1
        if svg_count >= 1:
            # Check if this is near "How can I help you today?"
            near_welcome = False
            for j in range(i, min(i+25, len(lines))):
                if 'How can I help you today?' in lines[j]:
                    near_welcome = True
                    break
            if near_welcome:
                # Find end of SVG
                for k in range(i, min(i+30, len(lines))):
                    if '</svg>' in lines[k]:
                        indent = '                  '
                        lines[i:k+1] = [indent + '<img src={authToken ? teenZenLogo : teenZenLogoDark} alt="Teen Zen" className="h-20 w-20 rounded-2xl" />']
                        content = '\n'.join(lines)
                        changes += 1
                        print(f"[8] Replaced welcome SVG with TeenZen logo")
                        break
                break

# 9. Update footer text
content = content.replace('© 2026 RAG-BOT INC', '© 2026 TEEN ZEN')

# 10. Replace "Ask a question about your docs..." placeholder
content = content.replace('Ask a question about your docs...', 'How are you feeling today?')

# 11. Update positioning statement
content = content.replace(
    'Ask anything about your documents or provide a prompt to start.',
    'AI-guided emotional growth with human support when you need it.'
)

with open(filepath, 'w') as f:
    f.write(content)

print(f"\n✅ Done! {changes} change groups applied")
print("\nNext: cd chatbot-rag/frontend && npm run build")
