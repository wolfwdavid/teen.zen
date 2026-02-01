<script>
  // Get data we saved during registration
  let email = localStorage.getItem('userEmail') || 'Guest';
  let token = localStorage.getItem('token');

  function logout() {
    localStorage.clear();
    window.location.hash = '#/login';
  }
</script>

<div class="chat-container">
  <nav>
    <span>Teen Zen Chat</span>
    <button on:click={logout}>Logout</button>
  </nav>

  <main>
    <h1>Welcome, {email}!</h1>
    <div class="chat-window">
      <p class="bot-msg">Hello! I'm your RAG assistant. How can I help you today?</p>
    </div>
    
    <div class="input-area">
      <input type="text" placeholder="Type your message..." disabled />
      <button disabled>Send</button>
    </div>
  </main>
</div>

<style>
  .chat-container { font-family: sans-serif; height: 100vh; display: flex; flex-direction: column; }
  nav { background: #4a90e2; color: white; padding: 1rem; display: flex; justify-content: space-between; }
  main { flex: 1; display: flex; flex-direction: column; align-items: center; padding: 2rem; }
  .chat-window { border: 1px solid #ddd; width: 100%; max-width: 600px; height: 300px; padding: 1rem; background: #f9f9f9; }
  .input-area { margin-top: 1rem; display: flex; gap: 10px; width: 100%; max-width: 600px; }
  input { flex: 1; padding: 10px; }
  button { padding: 10px 20px; cursor: pointer; }
</style>