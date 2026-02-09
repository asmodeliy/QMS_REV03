(function(){
    const chatBox = document.getElementById('chatBox');
    const promptEl = document.getElementById('prompt');
    const sendBtn = document.getElementById('sendBtn');
    const maxTokensEl = document.getElementById('maxTokens');
    const tempEl = document.getElementById('temp');
  
    function appendMessage(from, text){
      const wrap = document.createElement('div');
      wrap.style.marginBottom = '8px';
      wrap.innerHTML = `<strong>${from}:</strong> <div style="margin-top:6px">${text.replace(/\n/g,'<br/>')}</div>`;
      chatBox.appendChild(wrap);
      chatBox.scrollTop = chatBox.scrollHeight;
    }
  
    async function send(){
      const prompt = promptEl.value.trim();
      if(!prompt) return;
      appendMessage('You', prompt);
      promptEl.value = '';
      sendBtn.disabled = true;
      appendMessage('LLM', '...working...');
      try{
        const resp = await fetch('/api/llm/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt, max_tokens: parseInt(maxTokensEl.value||256), temperature: parseFloat(tempEl.value||0.2) })
        });
        const data = await resp.json();
        // remove the last '...working...' message
        chatBox.lastChild.remove();
        if(data.ok){
          appendMessage('LLM', data.response);
        } else {
          appendMessage('LLM', 'Error: ' + (data.error || 'Unknown'));
        }
      } catch (e){
        chatBox.lastChild.remove();
        appendMessage('LLM', 'Request failed: ' + e.toString());
      } finally {
        sendBtn.disabled = false;
        promptEl.focus();
      }
    }
  
    sendBtn.addEventListener('click', send);
    promptEl.addEventListener('keydown', function(ev){ if(ev.key==='Enter' && (ev.ctrlKey||ev.metaKey)) { send(); }});
  })();