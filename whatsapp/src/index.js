import 'dotenv/config'
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
  }
})

const mether = new METHERClient(process.env.METHER_BACKEND_URL || 'http://localhost:8000')

// QR code → terminal
client.on('qr', (qr) => {
  qrcode.generate(qr, { small: true })
  console.log('[METHER-WA] Scan QR code above with WhatsApp')
  // Also send QR to METHER backend for display in dashboard
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
  // Skip status broadcasts
  if (msg.from === 'status@broadcast') return
  
  const contact = await msg.getContact()
  const chat = await msg.getChat()
  
  const payload = {
    id: msg.id._serialized,
    from: msg.from,
    fromName: contact.pushname || contact.name || msg.from,
    body: msg.body,
    timestamp: msg.timestamp,
    isGroup: chat.isGroup,
    groupName: chat.isGroup ? chat.name : null,
    hasMedia: msg.hasMedia,
    type: msg.type
  }
  
  console.log(`[METHER-WA] Message from ${payload.fromName}: ${payload.body}`)
  
  // Forward to METHER backend
  await mether.notify('whatsapp.message', payload)
})

// EXPRESS API SERVER (METHER backend calls these)
const app = express()
app.use(express.json())

// Send a message
app.post('/send', async (req, res) => {
  const { to, message } = req.body
  
  if (!to || !message) {
    return res.status(400).json({ error: 'to and message required' })
  }
  
  try {
    // Format number: if no @c.us suffix, add it
    const chatId = to.includes('@') ? to : `${to}@c.us`
    await client.sendMessage(chatId, message)
    
    console.log(`[METHER-WA] Sent to ${to}: ${message}`)
    res.json({ success: true, to, message })
  } catch (err) {
    console.error('[METHER-WA] Send error:', err)
    res.status(500).json({ error: err.message })
  }
})

// Get recent chats
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

// Get messages from a chat
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

// Status check
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

// Initialize WhatsApp
client.initialize()
