<template>
  <div class="page-container fade-in">
    <header class="page-header mb-6">
      <h1 class="text-3xl font-bold">AI Chat</h1>
      <p class="text-secondary mt-2">Interactive conversational AI with context awareness.</p>
    </header>

    <div class="chat-container">
      <!-- Session Sidebar (Desktop) -->
      <aside class="sessions-sidebar glass">
        <BaseButton variant="primary" class="w-full mb-4" @click="startNewChat">
          + New Chat
        </BaseButton>
        <div class="session-list">
          <div v-for="s in sessions" :key="s.id" class="session-item" :class="{ active: currentSessionId === s.id }">
            {{ s.title }}
          </div>
        </div>
      </aside>

      <!-- Main Chat Area -->
      <BaseCard class="chat-wrapper glass">
        <div ref="messageContainer" class="messages-area">
          <div v-if="messages.length === 0" class="empty-state">
            <span class="icon text-4xl mb-4">✨</span>
            <p>How can I help you today?</p>
          </div>
          
          <div v-for="(msg, index) in messages" :key="index" :class="['message', msg.role]">
            <div class="message-content">
              <div class="role-badge">{{ msg.role === 'user' ? 'You' : 'AI' }}</div>
              <div class="text">{{ msg.content }}</div>
            </div>
          </div>

          <div v-if="isStreaming" class="message assistant streaming">
            <div class="message-content">
              <div class="role-badge">AI</div>
              <div class="text">{{ streamingContent }}<span class="cursor">|</span></div>
            </div>
          </div>
        </div>

        <template #footer>
          <form @submit.prevent="sendMessage" class="input-area">
            <input 
              v-model="userInput" 
              type="text" 
              placeholder="Type your message..." 
              :disabled="isStreaming"
              class="message-input"
            />
            <BaseButton :loading="isStreaming" :disabled="!userInput.trim()">
              Send
            </BaseButton>
          </form>
        </template>
      </BaseCard>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Chat Page — Real-time Streaming AI Interface
 */

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const userInput = ref('');
const messages = ref<Message[]>([]);
const isStreaming = ref(false);
const streamingContent = ref('');
const workspaceStore = useWorkspaceStore();
const currentSessionId = ref<string | null>(null);
const sessions = ref<{ id: string, title: string }[]>([]);
const messageContainer = ref<HTMLElement | null>(null);

// Auto-scroll to bottom
watch([messages, streamingContent], () => {
  nextTick(() => {
    if (messageContainer.value) {
      messageContainer.value.scrollTop = messageContainer.value.scrollHeight;
    }
  });
});

async function sendMessage() {
  if (!userInput.value.trim() || isStreaming.value) return;

  const content = userInput.value;
  userInput.value = '';
  
  // 1. Add user message
  messages.value.push({ role: 'user', content });
  
  // 2. Prepare streaming
  isStreaming.value = true;
  streamingContent.value = '';

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        message: content,
        session_id: currentSessionId.value,
        workspace_id: workspaceStore.currentWorkspaceId
      })
    });

    if (!response.body) throw new Error('No response body');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n\n');

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const data = JSON.parse(line.replace('data: ', ''));
        
        if (data.token) {
          streamingContent.value += data.token;
        } else if (data.session_id && !currentSessionId.value) {
          currentSessionId.value = data.session_id;
        }
      }
    }

    // 3. Finalize assistant message
    messages.value.push({ role: 'assistant', content: streamingContent.value });
    streamingContent.value = '';
  } catch (err) {
    console.error('Chat error:', err);
    messages.value.push({ role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' });
  } finally {
    isStreaming.value = false;
  }
}

function startNewChat() {
  messages.value = [];
  currentSessionId.value = null;
}
</script>

<style scoped>
.chat-container {
  display: flex;
  gap: 24px;
  height: calc(100vh - 180px);
}

.sessions-sidebar {
  width: 240px;
  padding: 20px;
  border-radius: var(--radius-lg);
  display: none; /* Hide on small screens */
}

@media (min-width: 1024px) {
  .sessions-sidebar { display: block; }
}

.chat-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-secondary);
}

.message {
  display: flex;
  flex-direction: column;
  max-width: 85%;
}

.message.user {
  align-self: flex-end;
}

.message.user .message-content {
  background: var(--color-primary);
  color: white;
  border-radius: var(--radius-lg) var(--radius-lg) 0 var(--radius-lg);
}

.message.assistant .message-content {
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg) var(--radius-lg) var(--radius-lg) 0;
}

.message-content {
  padding: 12px 16px;
  position: relative;
}

.role-badge {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 4px;
  opacity: 0.8;
}

.text {
  font-size: 0.95rem;
  line-height: 1.5;
  white-space: pre-wrap;
}

.input-area {
  display: flex;
  gap: 12px;
}

.message-input {
  flex: 1;
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 10px 16px;
  color: var(--color-text-primary);
  outline: none;
  transition: border-color 0.2s;
}

.message-input:focus {
  border-color: var(--color-primary);
}

.cursor {
  display: inline-block;
  width: 2px;
  animation: blink 1s infinite;
  color: var(--color-primary);
  margin-left: 2px;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
