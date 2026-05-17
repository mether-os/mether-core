import axios from 'axios'

export class METHERClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl
    this.client = axios.create({ baseURL: baseUrl, timeout: 5000 })
  }
  
  async notify(event, data) {
    try {
      await this.client.post('/whatsapp/event', { event, data })
    } catch (err) {
      // Backend may not be ready yet, log and continue
      console.log(`[METHER-WA] Could not notify backend: ${err.message}`)
    }
  }
}
