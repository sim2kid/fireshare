import React from 'react'

let isLocalhost = (window.location.hostname.indexOf('localhost') >= 0 || window.location.hostname.indexOf('127.0.0.1') >= 0) && window.location.port !== '';
export const getServedBy = () => {
  return isLocalhost
    ? 'flask'
    : 'nginx'
}

export const getUrl = () => {
  const portWithColon = window.location.port ? `:${window.location.port}` : ''
  return isLocalhost
    ? `http://${window.location.hostname}:${process.env.REACT_APP_SERVER_PORT || window.location.port}`
    : `${window.location.protocol}//${window.location.hostname}${portWithColon}`
}

export const getPublicWatchUrl = () => {
  const shareableLinkDomain = getSetting('ui_config')?.['shareable_link_domain']
  if (shareableLinkDomain) {
    return `${shareableLinkDomain}/w/`
  }
  const portWithColon = window.location.port ? `:${window.location.port}` : ''
  return isLocalhost
    ? `http://${window.location.hostname}:${process.env.REACT_APP_SERVER_PORT || window.location.port}/#/w/`
    : `${window.location.protocol}//${window.location.hostname}${portWithColon}/w/`
}

export const getVideoPath = (id, extension) => {
  if (extension === '.mkv') {
    return `${id}-1.mp4`
  }
  return `${id}${extension}`
}

export const useDebounce = (value, delay) => {
  const [debouncedValue, setDebouncedValue] = React.useState(value)

  React.useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay)
    return () => {
      clearTimeout(timer)
    }
  }, [value, delay])

  return debouncedValue
}

export const getSettings = () => localStorage.getItem('config') && JSON.parse(localStorage.getItem('config'))
export const getSetting = (setting) =>
  localStorage.getItem('config') && JSON.parse(localStorage.getItem('config'))[setting]
export const setSettings = (settings) => localStorage.setItem('config', JSON.stringify(settings))
export const setSetting = (setting, value) => {
  if (localStorage.getItem('config')) {
    const settings = JSON.parse(localStorage.getItem('config'))
    localStorage.setItem('config', JSON.stringify({ ...settings, [setting]: value }))
  } else {
    localStorage.setItem('config', JSON.stringify({ [setting]: value }))
  }
}

export const toHHMMSS = (secs) => {
  var sec_num = parseInt(secs, 10)
  var hours = Math.floor(sec_num / 3600)
  var minutes = Math.floor(sec_num / 60) % 60
  var seconds = sec_num % 60

  return [hours, minutes, seconds]
    .map((v) => (v < 10 ? '0' + v : v))
    .filter((v, i) => v !== '00' || i > 0)
    .join(':')
}

export const copyToClipboard = (textToCopy) => {
  // navigator clipboard api needs a secure context (https)
  if (navigator.clipboard && window.isSecureContext) {
    // navigator clipboard api method'
    return navigator.clipboard.writeText(textToCopy)
  } else {
    console.log('test')
    // text area method
    let textArea = document.createElement('textarea')
    textArea.value = textToCopy
    // make the textarea out of viewport
    textArea.style.position = 'fixed'
    textArea.style.left = '-999999px'
    textArea.style.top = '-999999px'
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()
    return new Promise((res, rej) => {
      // here the magic happens
      document.execCommand('copy') ? res() : rej()
      textArea.remove()
    })
  }
}

/**
 * Gets the URL for a specific video quality
 * @param {string} videoId - The video ID
 * @param {string} quality - Quality ('720p', '1080p', or 'original')
 * @param {string} extension - Video file extension (e.g., '.mp4', '.mkv')
 * @returns {string} Video URL
 */
export const getVideoUrl = (videoId, quality, extension) => {
  const URL = getUrl()
  const SERVED_BY = getServedBy()
  const codecs = getClientSupportedCodecs().join(',')

  if (quality === '720p' || quality === '1080p') {
    if (SERVED_BY === 'nginx') {
      return `${URL}/_content/derived/${videoId}/${videoId}-${quality}.mp4`
    }
    // Use new ffmpeg-backed streaming endpoint
    return `${URL}/api/stream?id=${videoId}&quality=${quality}&codecs=${encodeURIComponent(codecs)}&codec_try=0`
  }

  // Original quality
  if (SERVED_BY === 'nginx') {
    const videoPath = getVideoPath(videoId, extension)
    return `${URL}/_content/video/${videoPath}`
  }
  // Use new ffmpeg-backed streaming endpoint for original
  if (extension === '.mkv') {
    return `${URL}/api/stream?id=${videoId}&subid=1&codecs=${encodeURIComponent(codecs)}&codec_try=0`
  }
  return `${URL}/api/stream?id=${videoId}&codecs=${encodeURIComponent(codecs)}&codec_try=0`
}

/**
 * Generates video sources array for Video.js player with quality options
 * Defaults to original quality, with 720p and 1080p as alternatives
 * @param {string} videoId - The video ID
 * @param {Object} videoInfo - Video info object containing has_720p, has_1080p flags
 * @param {string} extension - Video file extension (e.g., '.mp4', '.mkv')
 * @returns {Array} Array of video sources for Video.js
 */
export const getVideoSources = (videoId, videoInfo, extension) => {
  const sources = []

  const has720p = videoInfo?.has_720p
  const has1080p = videoInfo?.has_1080p

  // Add 720p
  if (has720p) {
    sources.push({
      src: getVideoUrl(videoId, '720p', extension),
      type: 'video/mp4',
      label: '720p',
    })
  }

  // Add 1080p
  if (has1080p) {
    sources.push({
      src: getVideoUrl(videoId, '1080p', extension),
      type: 'video/mp4',
      label: '1080p',
    })
  }

  // Add original quality - always selected by default
  sources.push({
    src: getVideoUrl(videoId, 'original', extension),
    type: 'video/mp4',
    label: 'Original',
    selected: true, // Always default to original quality
  })

  return sources
}

// Determine client-supported codecs in preference order (full list; H264 always included)
export const getClientSupportedCodecs = () => {
  const video = document.createElement('video')
  if (!video || typeof video.canPlayType !== 'function') {
    return ['H264']
  }
  const candidates = [
    { name: 'H264', type: 'video/mp4; codecs="avc1.42E01E, mp4a.40.2"' },
    { name: 'AV1', type: 'video/mp4; codecs="av01.0.05M.08, mp4a.40.2"' },
    { name: 'VP9', type: 'video/webm; codecs="vp9, opus"' },
    { name: 'VP8', type: 'video/webm; codecs="vp8, vorbis"' },
    { name: 'HEVC', type: 'video/mp4; codecs="hvc1.1.6.L93.B0"' },
    { name: 'MPEG4', type: 'video/mp4; codecs="mp4v.20.9"' },
    { name: 'MPEG2', type: 'video/mp2t' },
  ]
  // Rank by canPlayType result: probably > maybe > ''
  const ranked = candidates
    .map(c => ({
      name: c.name,
      support: video.canPlayType(c.type) || ''
    }))
    .filter(c => c.support && c.support.length > 0)
    .sort((a, b) => {
      const score = v => (v.support === 'probably' ? 2 : v.support === 'maybe' ? 1 : 0)
      return score(b) - score(a)
    })
    .map(c => c.name)

  // Always ensure H264 is present as a safe fallback
  const out = []
  ranked.forEach(n => { if (!out.includes(n)) out.push(n) })
  if (!out.includes('H264')) out.push('H264')
  return out
}
