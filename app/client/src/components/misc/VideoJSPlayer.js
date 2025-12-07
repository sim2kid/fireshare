import React, { useEffect, useRef } from 'react'
import videojs from 'video.js'
import 'video.js/dist/video-js.css'

// Import and register the quality selector plugin
import qualitySelectorPlugin from '@silvermine/videojs-quality-selector'
import '@silvermine/videojs-quality-selector/dist/css/quality-selector.css'
import { getUrl } from '../../common/utils'

// Register the quality selector plugin with videojs
qualitySelectorPlugin(videojs)

// Tolerance threshold for checking if player is already at the desired start time (in seconds)
const SEEK_TOLERANCE_SECONDS = 0.5

const VideoJSPlayer = ({
  sources,
  poster,
  autoplay = false,
  controls = true,
  onTimeUpdate,
  onReady,
  startTime,
  durationHint,
  className,
  style,
  videoId,
}) => {
  const videoRef = useRef(null)
  const playerRef = useRef(null)
  const originalDurationRef = useRef(null)
  const onTimeUpdateRef = useRef(onTimeUpdate)
  const onReadyRef = useRef(onReady)
  // Track failed codec attempts locally (per player instance)
  const failedCodecsRef = useRef(new Set())
  // Cache whether the server supports transcoding for the current stream URL
  const transcodingEnabledRef = useRef(null)

  // Keep refs updated with latest callback values
  useEffect(() => {
    onTimeUpdateRef.current = onTimeUpdate
    onReadyRef.current = onReady
  }, [onTimeUpdate, onReady])

  useEffect(() => {
    // Make sure Video.js player is only initialized once
    if (!playerRef.current) {
      const videoElement = videoRef.current

      if (!videoElement) return

      const player = (playerRef.current = videojs(videoElement, {
        autoplay,
        controls,
        responsive: true,
        fluid: true,
        poster,
        preload: 'auto',
        html5: {
          vhs: {
            overrideNative: true,
          },
          nativeVideoTracks: false,
          nativeAudioTracks: false,
          nativeTextTracks: false,
        },
        controlBar: {
          children: [
            'playToggle',
            'volumePanel',
            'currentTimeDisplay',
            'timeDivider',
            'durationDisplay',
            'progressControl',
            'liveDisplay',
            'seekToLive',
            'remainingTimeDisplay',
            'customControlSpacer',
            'playbackRateMenuButton',
            'chaptersButton',
            'descriptionsButton',
            'subsCapsButton',
            'audioTrackButton',
            'qualitySelector',
            'fullscreenToggle',
          ],
        },
      }))

      // Set up sources
      if (sources && sources.length > 0) {
        player.src(sources)
      }

      // Handle time updates using ref to avoid recreating player
      player.on('timeupdate', () => {
        const currentTime = player.currentTime()
        if (onTimeUpdateRef.current) {
          onTimeUpdateRef.current({ playedSeconds: currentTime || 0 })
        }
      })

      // Handle playback errors client-side: track failures and try next codec until list exhausted,
      // but ONLY if the server supports transcoding for stream negotiation.
      player.on('error', async () => {
        try {
          const currentSrc = player.currentSrc()
          if (!currentSrc) return
          const url = new URL(currentSrc)
          const codecs = url.searchParams.get('codecs') || ''
          const codecTry = parseInt(url.searchParams.get('codec_try') || '0')
          const list = codecs.split(',').map(s => s.trim()).filter(Boolean)
          if (!list.length) return
          // Check server capability once via a lightweight capability endpoint
          if (transcodingEnabledRef.current === null) {
            try {
              const res = await fetch(`${getUrl()}/api/transcoding/enabled`)
              if (res.ok) {
                const data = await res.json().catch(() => ({}))
                transcodingEnabledRef.current = !!data.enabled
              } else {
                transcodingEnabledRef.current = false
              }
            } catch (e) {
              transcodingEnabledRef.current = false
            }
          }
          if (!transcodingEnabledRef.current) {
            // Server does not transcode; don't iterate codecs
            return
          }
          // Record failure locally for this client/session
          const failed = list[codecTry]
          if (failed) {
            try { failedCodecsRef.current.add(failed.toUpperCase()) } catch (_) {}
            // Optionally persist per-video in sessionStorage to avoid re-trying on re-open within the same tab
            try {
              const key = `fs_failed_codecs_${videoId || 'unknown'}`
              const prev = JSON.parse(sessionStorage.getItem(key) || '[]')
              if (!prev.includes(failed)) {
                sessionStorage.setItem(key, JSON.stringify([...prev, failed]))
              }
            } catch (_) {}
          }
          // Try next codec until we exhaust the list
          if (codecTry < (list.length - 1)) {
            url.searchParams.set('codec_try', String(codecTry + 1))
            const t = player.currentTime()
            player.src({ src: url.toString(), type: 'video/mp4' })
            player.one('loadedmetadata', () => {
              try { player.currentTime(t) } catch {}
              player.play().catch(() => {})
            })
          }
        } catch (e) {
          // ignore
        }
      })

      // Seek to start time if provided
      if (startTime) {
        // Try to seek immediately when metadata is loaded
        player.one('loadedmetadata', () => {
          player.currentTime(startTime)
          // Apply duration hint after metadata if provided
          if (typeof durationHint === 'number' && durationHint > 0) {
            try { player.duration(durationHint) } catch (e) {}
          }
        })

        // Also seek when user manually plays if not already at the correct time
        // This handles cases where autoplay is blocked
        player.one('play', () => {
          if (Math.abs(player.currentTime() - startTime) > SEEK_TOLERANCE_SECONDS) {
            player.currentTime(startTime)
          }
        })
      }

      // Call onReady when player is ready using ref
      player.ready(() => {
        // Apply duration hint on ready if available (in case metadata isn't set yet)
        if (typeof durationHint === 'number' && durationHint > 0) {
          try { player.duration(durationHint) } catch (e) {}
          try { player.trigger('durationchange') } catch (e) {}
        }
        if (onReadyRef.current) {
          onReadyRef.current(player)
        }
      })
    } else {
      const player = playerRef.current

      // Update sources if they change
      if (sources && sources.length > 0) {
        const currentSrc = player.currentSrc()
        // Check if the current source is in the new sources array
        const sourceExists = sources.some(source => source.src === currentSrc)
        if (!sourceExists) {
          const currentTime = player.currentTime()
          player.src(sources)
          player.one('loadedmetadata', () => {
            player.currentTime(currentTime)
          })
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sources, poster, autoplay, controls, startTime, durationHint])

  // Update duration if the hint changes after initialization
  useEffect(() => {
    const player = playerRef.current
    if (!player) return

    // If we have a valid hint, monkey-patch player's duration getter so UI uses it.
    if (typeof durationHint === 'number' && isFinite(durationHint) && durationHint > 0) {
      // Save original once
      if (!originalDurationRef.current) {
        originalDurationRef.current = player.duration.bind(player)
      }
      // Override duration() to return our hint when called without args
      player.duration = function (...args) {
        if (args.length === 0) return durationHint
        // If someone tries to set duration, forward to original
        return originalDurationRef.current(...args)
      }
      // Notify controls to recalc remaining time
      try { player.trigger('durationchange') } catch (e) {}
      try { player.trigger('timeupdate') } catch (e) {}
    } else {
      // Restore original duration if previously patched
      if (originalDurationRef.current) {
        try { player.duration = originalDurationRef.current } catch (e) {}
        originalDurationRef.current = null
        try { player.trigger('durationchange') } catch (e) {}
      }
    }
  }, [durationHint])

  // Dispose the Video.js player when the functional component unmounts
  useEffect(() => {
    const player = playerRef.current

    return () => {
      if (player && !player.isDisposed()) {
        // Restore original duration method if patched
        if (originalDurationRef.current) {
          try { player.duration = originalDurationRef.current } catch (e) {}
          originalDurationRef.current = null
        }
        player.dispose()
        playerRef.current = null
      }
    }
  }, [])

  return (
    <div data-vjs-player className={className} style={style}>
      <video ref={videoRef} className="video-js vjs-big-play-centered" />
    </div>
  )
}

export default VideoJSPlayer
