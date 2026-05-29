import axios from 'axios'

export class METHERClient {
  constructor(baseUrl, apiKey) {
    this.baseUrl = baseUrl
    const headers = {};
    if (apiKey) {
      headers['X-METHER-KEY'] = apiKey;
    }
    this.client = axios.create({ baseURL: baseUrl, timeout: 5000, headers })
  }
  
  async notify(event, data) {
    try {
      await this.client.post('/api/v1/whatsapp/event', { event, data })
    } catch (err) {
      // Backend may not be ready yet, log and continue
      console.log(`[METHER-WA] Could not notify backend: ${err.message}`)
    }
  }
}
