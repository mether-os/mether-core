import 'dotenv/config'
// METHER OS WhatsApp Bridge
import pkg from 'whatsapp-web.js'
const { Client, LocalAuth } = pkg
import qrcode from 'qrcode-terminal'
import express from 'express'
import { METHERClient } from './mether-client.js'

// WhatsApp Client setup
const client = new Client({
  authStrategy: new LocalAuth({ dataPath: process.env.SESSION_DATA_PATH || './.wwebjs_auth' }),
  puppeteer: {
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  },
  webVersionCache: {
    type: 'remote',
    remotePath: 'https://raw.githubusercontent.com/wppconnect-team/wa-version/main/html/2.2412.54.html'
  }
})

const mether = new METHERClient(process.env.METHER_BACKEND_URL || 'http://localhost:8000')

// Keep client warmed up
setInterval(async () => {
  try { await client.getState(); } catch(e) {}
}, 30000);

// QR code → terminal
client.on('qr', (qr) => {
  qrcode.generate(qr, { small: true })
  console.log('[METHER-WA] Scan QR code above with WhatsApp')
  mether.notify('whatsapp.qr', { qr })
})

client.on('ready', () => {
  console.log('[METHER-WA] WhatsApp connected!')
  mether.notify('whatsapp.ready', { status: 'connected' })
})

client.on('disconnected', (reason) => {
  console.log('[METHER-WA] Disconnected:', reason)
  mether.notify('whatsapp.disconnected', { reason })
})

// INCOMING MESSAGES
client.on('message', async (msg) => {
  if (msg.from === 'status@broadcast') return
  
  const contact = await msg.getContact()
  const chat = await msg.getChat()
  
  const payload = {
    id: msg.id._serialized,
    from: msg.from,
    contactNumber: contact.number || null,
    fromName: contact.name || contact.pushname || msg.from,
    body: msg.body,
    timestamp: msg.timestamp,
    isGroup: chat.isGroup,
    groupName: chat.isGroup ? chat.name : null,
    hasMedia: msg.hasMedia,
    type: msg.type
  }
  
  console.log(`[METHER-WA] Message from ${payload.fromName}: ${payload.body}`)
  await mether.notify('whatsapp.message', payload)
})

// EXPRESS API SERVER
const app = express()
app.use(express.json())

// Cache contacts to prevent 5-10 second delays on every message
let contactsCache = []
let lastCacheUpdate = 0
const CACHE_TTL = 1000 * 60 * 60 // 1 hour

async function getCachedContacts() {
  if (contactsCache.length === 0 || Date.now() - lastCacheUpdate > CACHE_TTL) {
    contactsCache = await client.getContacts();
    lastCacheUpdate = Date.now();
  }
  return contactsCache;
}

app.get('/contacts', async (req, res) => {
  try {
    const contacts = await getCachedContacts()
    const simplified = contacts.map(c => ({
      id: c.id._serialized,
      name: c.name || c.pushname || null,
      shortName: c.shortName || null
    })).filter(c => c.name)
    res.json(simplified)
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

app.post('/resolve', async (req, res) => {
  const { query } = req.body
  if (!query) return res.status(400).json({ error: 'query required' })
  
  try {
    const contacts = await getCachedContacts()
    const search = query.toLowerCase()
    
    let matches = []
    for (const c of contacts) {
      if (!c.name && !c.pushname && !c.shortName) continue;
      const fullName = (c.name || c.pushname || "").toLowerCase()
      const shortName = (c.shortName || "").toLowerCase()
      
      if (fullName.includes(search) || shortName.includes(search)) {
        matches.push({
          id: c.id._serialized,
          name: c.name || c.pushname,
          confidence: fullName === search ? 100 : fullName.startsWith(search) ? 80 : 50
        })
      }
    }
    
    matches.sort((a, b) => b.confidence - a.confidence)
    const topMatches = matches.slice(0, 3)
    
    if (topMatches.length === 0) {
      return res.status(404).json({ error: 'Contact not found' })
    }
    
    res.json(topMatches[0]) // Return best match directly
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

app.post('/send', async (req, res) => {
  const { to, message } = req.body
  if (!to || !message) {
    return res.status(400).json({ error: 'to and message required' })
  }
  
  try {
    let chatId = to
    // Backend already resolves, but fallback safety:
    if (!to.includes('@') && !/^\d+$/.test(to.replace(/\+/g, ''))) {
      const contacts = await getCachedContacts()
      const search = to.toLowerCase()
      const match = contacts.find(c => 
        (c.name || c.pushname || "").toLowerCase().includes(search) ||
        (c.shortName || "").toLowerCase().includes(search)
      )
      if (match) chatId = match.id._serialized
    } else {
      chatId = to.includes('@') ? to : `${to.replace(/\+/g, '')}@c.us`
    }

    await client.sendMessage(chatId, message)
    console.log(`[METHER-WA] Sent to ${chatId}: ${message}`)
    res.json({ success: true, to: chatId, message })
  } catch (err) {
    console.error('[METHER-WA] Send error:', err)
    res.status(500).json({ error: err.message })
  }
})

app.get('/chats', async (req, res) => {
  try {
    const chats = await client.getChats()
    const simplified = chats.slice(0, 20).map(c => ({
      id: c.id._serialized,
      name: c.name,
      isGroup: c.isGroup,
      unreadCount: c.unreadCount,
      lastMessage: c.lastMessage?.body?.substring(0, 100)
    }))
    res.json({ chats: simplified })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

app.get('/messages/:chatId', async (req, res) => {
  try {
    const chat = await client.getChatById(req.params.chatId)
    const messages = await chat.fetchMessages({ limit: 20 })
    const simplified = messages.map(m => ({
      id: m.id._serialized,
      from: m.from,
      body: m.body,
      timestamp: m.timestamp,
      fromMe: m.fromMe,
      type: m.type
    }))
    res.json({ messages: simplified })
  } catch (err) {
    res.status(500).json({ error: err.message })
  }
})

app.get('/status', (req, res) => {
  const state = client.info ? 'connected' : 'disconnected'
  res.json({ 
    status: state,
    phone: client.info?.wid?.user || null
  })
})

const PORT = process.env.WHATSAPP_PORT || 3001
app.listen(PORT, () => {
  console.log(`[METHER-WA] API server on port ${PORT}`)
})

client.initialize()
