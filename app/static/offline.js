/**
 * offline.js — For Glory Offline-First Layer
 *
 * Responsabilidades:
 * - Salva mensagens enviadas em IndexedDB antes de ir ao servidor
 * - Mantém fila de saída quando WebSocket está desconectado
 * - Flush automático na reconexão
 * - Cache local de mensagens (leitura offline)
 * - Cache de noticias e politicos (leitura offline)
 */

(function() {
'use strict';

const DB_NAME    = 'forglory_offline';
const DB_VERSION = 1;

// ── Abre o banco ─────────────────────────────────────────────────────────────
let _db = null;

function openDB() {
  return new Promise((resolve, reject) => {
    if (_db) return resolve(_db);
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;

      // Mensagens locais (histórico offline)
      if (!db.objectStoreNames.contains('messages')) {
        const ms = db.createObjectStore('messages', { keyPath: '_local_id', autoIncrement: true });
        ms.createIndex('chat_key', 'chat_key', { unique: false });
        ms.createIndex('status',   'status',   { unique: false });
      }

      // Fila de saída (pendente de envio)
      if (!db.objectStoreNames.contains('queue_outbound')) {
        const qs = db.createObjectStore('queue_outbound', { keyPath: '_qid', autoIncrement: true });
        qs.createIndex('ts', 'ts', { unique: false });
      }

      // Cache de mídia (URLs já visitadas)
      if (!db.objectStoreNames.contains('media_cache')) {
        const mc = db.createObjectStore('media_cache', { keyPath: 'url' });
        mc.createIndex('accessed_at', 'accessed_at', { unique: false });
      }

      // Cache de notícias
      if (!db.objectStoreNames.contains('news_cache')) {
        const nc = db.createObjectStore('news_cache', { keyPath: 'level' });
      }

      // Cache de políticos
      if (!db.objectStoreNames.contains('politician_cache')) {
        const pc = db.createObjectStore('politician_cache', { keyPath: 'id' });
        pc.createIndex('updated_at', 'updated_at', { unique: false });
      }
    };
    req.onsuccess  = (e) => { _db = e.target.result; resolve(_db); };
    req.onerror    = (e) => { console.warn('[Offline] IndexedDB error:', e.target.error); reject(e.target.error); };
  });
}

async function getDB() {
  try { return await openDB(); }
  catch(e) { console.warn('[Offline] DB unavailable:', e); return null; }
}

// ── Helpers genéricos ─────────────────────────────────────────────────────────
function txGet(db, store, key) {
  return new Promise((resolve) => {
    try {
      const tx  = db.transaction(store, 'readonly');
      const req = tx.objectStore(store).get(key);
      req.onsuccess = () => resolve(req.result);
      req.onerror   = () => resolve(null);
    } catch(e) { resolve(null); }
  });
}

function txPut(db, store, obj) {
  return new Promise((resolve) => {
    try {
      const tx  = db.transaction(store, 'readwrite');
      const req = tx.objectStore(store).put(obj);
      req.onsuccess = () => resolve(req.result);
      req.onerror   = () => resolve(null);
    } catch(e) { resolve(null); }
  });
}

function txAdd(db, store, obj) {
  return new Promise((resolve) => {
    try {
      const tx  = db.transaction(store, 'readwrite');
      const req = tx.objectStore(store).add(obj);
      req.onsuccess = () => resolve(req.result);
      req.onerror   = () => resolve(null);
    } catch(e) { resolve(null); }
  });
}

function txDelete(db, store, key) {
  return new Promise((resolve) => {
    try {
      const tx  = db.transaction(store, 'readwrite');
      tx.objectStore(store).delete(key);
      tx.oncomplete = () => resolve(true);
      tx.onerror    = () => resolve(false);
    } catch(e) { resolve(false); }
  });
}

function txGetAll(db, store, indexName, indexValue) {
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(store, 'readonly');
      const os = tx.objectStore(store);
      let req;
      if (indexName && indexValue !== undefined) {
        req = os.index(indexName).getAll(indexValue);
      } else {
        req = os.getAll();
      }
      req.onsuccess = () => resolve(req.result || []);
      req.onerror   = () => resolve([]);
    } catch(e) { resolve([]); }
  });
}

// ── API pública: Mensagens ────────────────────────────────────────────────────

/**
 * Salva uma mensagem local antes de enviar.
 * Retorna o _local_id gerado.
 */
async function saveMessageLocal(chatKey, content, senderId, senderName, senderAvatar) {
  const db = await getDB();
  if (!db) return null;
  const msg = {
    chat_key:      chatKey,
    content:       content,
    sender_id:     senderId,
    sender_name:   senderName,
    sender_avatar: senderAvatar,
    status:        'pending',   // pending | sent | delivered | read
    ts:            Date.now(),
    offline:       false,
  };
  return txAdd(db, 'messages', msg);
}

/**
 * Marca mensagem local como enviada (atualiza status).
 */
async function markMessageSent(localId, serverId) {
  const db = await getDB();
  if (!db) return;
  const msg = await txGet(db, 'messages', localId);
  if (!msg) return;
  msg.status    = 'sent';
  msg.server_id = serverId;
  await txPut(db, 'messages', msg);
}

/**
 * Carrega histórico local de um chat.
 */
async function getLocalMessages(chatKey) {
  const db = await getDB();
  if (!db) return [];
  return txGetAll(db, 'messages', 'chat_key', chatKey);
}

// ── API pública: Fila de saída ────────────────────────────────────────────────

/**
 * Enfileira uma mensagem para envio quando WS reconectar.
 */
async function enqueueOutbound(chatChannel, content) {
  const db = await getDB();
  if (!db) return;
  await txAdd(db, 'queue_outbound', {
    channel: chatChannel,
    content: content,
    ts:      Date.now(),
  });
}

/**
 * Retorna todas as mensagens pendentes em ordem cronológica.
 */
async function getPendingOutbound() {
  const db = await getDB();
  if (!db) return [];
  const all = await txGetAll(db, 'queue_outbound');
  return all.sort((a, b) => a.ts - b.ts);
}

/**
 * Remove item da fila após envio bem-sucedido.
 */
async function dequeueOutbound(qid) {
  const db = await getDB();
  if (!db) return;
  await txDelete(db, 'queue_outbound', qid);
}

/**
 * Flush da fila: tenta enviar tudo via WS aberto.
 * Chamado automaticamente quando o WS abre (onopen).
 */
async function flushOutboundQueue(wsSendFn) {
  const pending = await getPendingOutbound();
  if (!pending.length) return;
  console.log(`[Offline] Flushing ${pending.length} mensagens pendentes...`);
  for (const item of pending) {
    try {
      wsSendFn(item.content, item.channel);
      await dequeueOutbound(item._qid);
      // Pequena pausa para não sobrecarregar
      await new Promise(r => setTimeout(r, 50));
    } catch(e) {
      console.warn('[Offline] Flush falhou para', item._qid, e);
      break; // Para no primeiro erro (WS fechou de novo)
    }
  }
}

// ── API pública: Cache de Notícias ────────────────────────────────────────────

async function cacheNews(level, articles) {
  const db = await getDB();
  if (!db) return;
  await txPut(db, 'news_cache', {
    level:      level,
    articles:   articles,
    cached_at:  Date.now(),
  });
}

async function getCachedNews(level, maxAgeMs = 5 * 60 * 1000) {
  const db = await getDB();
  if (!db) return null;
  const entry = await txGet(db, 'news_cache', level);
  if (!entry) return null;
  if (Date.now() - entry.cached_at > maxAgeMs) return null;
  return entry.articles;
}

// ── API pública: Cache de Políticos ──────────────────────────────────────────

async function cachePolitician(politician) {
  const db = await getDB();
  if (!db) return;
  await txPut(db, 'politician_cache', {
    ...politician,
    updated_at: Date.now(),
  });
}

async function getCachedPolitician(id) {
  const db = await getDB();
  if (!db) return null;
  return txGet(db, 'politician_cache', id);
}

// ── Inicialização e detecção de rede ─────────────────────────────────────────

let _isOnline = navigator.onLine;

window.addEventListener('online',  () => {
  _isOnline = true;
  console.log('[Offline] Conexão restaurada');
  document.dispatchEvent(new CustomEvent('fg:online'));
});
window.addEventListener('offline', () => {
  _isOnline = false;
  console.log('[Offline] Sem conexão');
  document.dispatchEvent(new CustomEvent('fg:offline'));
});

function isOnline() { return _isOnline; }

// ── Expõe API globalmente ─────────────────────────────────────────────────────
window.FGOffline = {
  isOnline,
  saveMessageLocal,
  markMessageSent,
  getLocalMessages,
  enqueueOutbound,
  getPendingOutbound,
  dequeueOutbound,
  flushOutboundQueue,
  cacheNews,
  getCachedNews,
  cachePolitician,
  getCachedPolitician,
};

// Inicializa DB em background
getDB().then(() => {
  console.log('[Offline] IndexedDB pronto');
}).catch(() => {
  console.warn('[Offline] IndexedDB indisponível (modo privado?)');
});

})();
