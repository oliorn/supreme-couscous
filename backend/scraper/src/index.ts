import { Hono } from 'hono'
import { cors } from 'hono/cors'
import axios from 'axios'
import * as cheerio from 'cheerio'

const app = new Hono()
app.use('*', cors()) 


app.get('/', (c) => c.text('✅ Scraper is running'))

app.get('/scrape', async (c) => {
  const url = c.req.query('url')
  if (!url) return c.json({ error: 'Missing ?url parameter' }, 400)

  try {
    const { data } = await axios.get(url, { timeout: 10000 })
    const $ = cheerio.load(data)

    const getMeta = (name: string) =>
      $(`meta[name='${name}']`).attr('content') ||
      $(`meta[property='${name}']`).attr('content')

    const title = $('title').text() || getMeta('og:title')
    const description = getMeta('description') || getMeta('og:description') || ''
    const favicon =
      $('link[rel="icon"]').attr('href') ||
      $('link[rel="shortcut icon"]').attr('href') ||
      '/favicon.ico'
    const image = getMeta('og:image')

    return c.json({
      url,
      title,
      description,
      favicon: favicon.startsWith('http') ? favicon : new URL(favicon, url).href,
      image
    })
  } catch (err: any) {
    return c.json({ error: 'Failed to scrape site', details: err.message }, 500)
  }
})

export default app
