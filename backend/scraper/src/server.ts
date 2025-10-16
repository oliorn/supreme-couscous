import app from './index'
import { serve } from '@hono/node-server' 

const port = 4001

serve({
  fetch: app.fetch,
  port,
})

console.log(`🚀 Scraper backend running at http://localhost:${port}`)
