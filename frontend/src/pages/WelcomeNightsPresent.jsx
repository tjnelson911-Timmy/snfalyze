import React, { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronRight, X, Maximize2, Minimize2 } from 'lucide-react'
import { getWNPresentData, markWNPresented } from '../services/api'

function WelcomeNightsPresent() {
  const { id } = useParams()
  const navigate = useNavigate()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [data, setData] = useState(null)
  const [currentSlide, setCurrentSlide] = useState(0)
  const [isFullscreen, setIsFullscreen] = useState(false)

  useEffect(() => {
    loadPresentation()
  }, [id])

  useEffect(() => {
    // Keyboard navigation
    const handleKeyDown = (e) => {
      if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'Enter') {
        e.preventDefault()
        nextSlide()
      } else if (e.key === 'ArrowLeft' || e.key === 'Backspace') {
        e.preventDefault()
        prevSlide()
      } else if (e.key === 'Escape') {
        if (document.fullscreenElement) {
          document.exitFullscreen()
        } else {
          navigate(`/welcome-nights/${id}/edit`)
        }
      } else if (e.key === 'f' || e.key === 'F') {
        toggleFullscreen()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [currentSlide, data])

  useEffect(() => {
    // Track fullscreen changes
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  const loadPresentation = async () => {
    setLoading(true)
    try {
      const presentData = await getWNPresentData(id)
      setData(presentData)
    } catch (err) {
      console.error('Error loading presentation:', err)
      setError('Failed to load presentation')
    } finally {
      setLoading(false)
    }
  }

  const nextSlide = useCallback(() => {
    if (data && currentSlide < data.slides.length - 1) {
      setCurrentSlide(currentSlide + 1)
    }
  }, [currentSlide, data])

  const prevSlide = useCallback(() => {
    if (currentSlide > 0) {
      setCurrentSlide(currentSlide - 1)
    }
  }, [currentSlide])

  const toggleFullscreen = async () => {
    if (!document.fullscreenElement) {
      await document.documentElement.requestFullscreen()
    } else {
      await document.exitFullscreen()
    }
  }

  const handleExit = async () => {
    if (document.fullscreenElement) {
      await document.exitFullscreen()
    }
    // Mark as presented if we got through slides
    if (data && currentSlide >= data.slides.length - 1) {
      try {
        await markWNPresented(id)
      } catch (e) {
        // Ignore errors
      }
    }
    navigate(`/welcome-nights/${id}/edit`)
  }

  if (loading) {
    return (
      <div className="wn-present-mode" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <div className="animate-spin" style={{ width: 60, height: 60, border: '4px solid #333', borderTopColor: '#fff', borderRadius: '50%' }} />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="wn-present-mode" style={{ justifyContent: 'center', alignItems: 'center', color: 'white' }}>
        <p>{error || 'No data'}</p>
        <button className="btn btn-secondary mt-4" onClick={() => navigate('/welcome-nights')}>
          Go Back
        </button>
      </div>
    )
  }

  const slide = data.slides[currentSlide]
  const brand = data.brand
  const facility = data.facility

  return (
    <div className="wn-present-mode" onClick={nextSlide}>
      <div className="wn-slide-container">
        <SlideRenderer
          slide={slide}
          brand={brand}
          facility={facility}
        />
      </div>

      <div className="wn-present-controls" onClick={(e) => e.stopPropagation()}>
        <button onClick={prevSlide} disabled={currentSlide === 0} title="Previous (Left Arrow)">
          <ChevronLeft size={24} />
        </button>

        <span className="wn-present-progress">
          {currentSlide + 1} / {data.total_slides}
        </span>

        <button onClick={nextSlide} disabled={currentSlide === data.slides.length - 1} title="Next (Right Arrow)">
          <ChevronRight size={24} />
        </button>

        <button onClick={toggleFullscreen} title="Toggle Fullscreen (F)">
          {isFullscreen ? <Minimize2 size={20} /> : <Maximize2 size={20} />}
        </button>

        <button onClick={handleExit} title="Exit (Escape)">
          <X size={20} />
        </button>
      </div>
    </div>
  )
}

function SlideRenderer({ slide, brand, facility }) {
  const { slide_type, payload } = slide

  const primaryColor = brand.primary_color || '#0b7280'
  const secondaryColor = brand.secondary_color || '#065a67'

  switch (slide_type) {
    case 'WelcomeIntro':
      return (
        <div className="wn-slide wn-slide-welcome" style={{ background: primaryColor }}>
          <h1>Welcome to {brand.name}</h1>
          <h2>{facility.name}</h2>
          <h3>Culture Night</h3>
        </div>
      )

    case 'RaffleBumper':
      return (
        <div className="wn-slide wn-slide-raffle">
          <h1>{payload?.title || 'RAFFLE TIME!'}</h1>
          <p>{payload?.subtitle || 'Time to draw a winner!'}</p>
        </div>
      )

    case 'HistoryBlock':
      return (
        <div className="wn-slide wn-slide-content">
          <div className="wn-slide-header" style={{ background: primaryColor }}>
            <h1>{payload?.title || 'Our History'}</h1>
          </div>
          <div className="wn-slide-body">
            {payload?.content?.items && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                {payload.content.items.map((item, idx) => (
                  <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
                    <div style={{
                      minWidth: 80,
                      fontWeight: 700,
                      fontSize: '1.5rem',
                      color: primaryColor
                    }}>
                      {item.year}
                    </div>
                    <div style={{ fontSize: '1.25rem', color: '#374151' }}>{item.text}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )

    case 'FootprintBlock':
      return (
        <div className="wn-slide wn-slide-content">
          <div className="wn-slide-header" style={{ background: primaryColor }}>
            <h1>{payload?.title || 'Our Growing Footprint'}</h1>
          </div>
          <div className="wn-slide-body">
            {payload?.content?.stats && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 40 }}>
                {payload.content.stats.map((stat, idx) => (
                  <div key={idx} style={{ textAlign: 'center', padding: 30, background: '#f3f4f6', borderRadius: 12 }}>
                    <div style={{ fontSize: '3rem', fontWeight: 700, color: primaryColor }}>
                      {stat.value}
                    </div>
                    <div style={{ fontSize: '1.25rem', color: '#6b7280', marginTop: 8 }}>
                      {stat.label}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )

    case 'RegionsBlock':
      return (
        <div className="wn-slide wn-slide-content">
          <div className="wn-slide-header" style={{ background: primaryColor }}>
            <h1>{payload?.title || 'Our Regions'}</h1>
          </div>
          <div className="wn-slide-body">
            {payload?.content?.regions && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                {payload.content.regions.map((region, idx) => (
                  <div key={idx} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: 20,
                    background: '#f3f4f6',
                    borderRadius: 8
                  }}>
                    <span style={{ fontSize: '1.5rem', fontWeight: 600 }}>{region.name}</span>
                    <span style={{ fontSize: '1.5rem', color: primaryColor, fontWeight: 700 }}>
                      {region.facilities} facilities
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )

    case 'CultureBlock':
      return (
        <div className="wn-slide wn-slide-content">
          <div className="wn-slide-header" style={{ background: primaryColor }}>
            <h1>{payload?.title || `The ${brand.name} Way`}</h1>
          </div>
          <div className="wn-slide-body" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <h2 style={{ fontSize: '2.5rem', color: primaryColor, marginBottom: 40 }}>
              {payload?.content?.subtitle || 'We are NOT corporate'}
            </h2>
            {payload?.content?.comparisons && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 20, maxWidth: 900 }}>
                <div style={{ textAlign: 'center', fontWeight: 700, color: primaryColor, fontSize: '1.25rem', paddingBottom: 10, borderBottom: `3px solid ${primaryColor}` }}>
                  {brand.name} Way
                </div>
                <div style={{ textAlign: 'center', fontWeight: 700, color: '#9ca3af', fontSize: '1.25rem', paddingBottom: 10, borderBottom: '3px solid #e5e7eb' }}>
                  Common Way
                </div>
                {payload.content.comparisons.map((comp, idx) => (
                  <React.Fragment key={idx}>
                    <div style={{ padding: 16, background: '#f0fdfa', borderRadius: 8, fontSize: '1.1rem' }}>
                      {comp[Object.keys(comp)[0]]}
                    </div>
                    <div style={{ padding: 16, background: '#f3f4f6', borderRadius: 8, fontSize: '1.1rem', color: '#6b7280' }}>
                      {comp[Object.keys(comp)[1]]}
                    </div>
                  </React.Fragment>
                ))}
              </div>
            )}
          </div>
        </div>
      )

    case 'GameSlide':
      return (
        <div className="wn-slide wn-slide-content">
          <div className="wn-slide-header" style={{ background: primaryColor }}>
            <h1>{payload?.title || 'Game Time!'}</h1>
          </div>
          <div className="wn-slide-body wn-slide-game">
            {payload?.value_label && (
              <h2>{payload.value_label}</h2>
            )}
            {payload?.rules && (
              <div className="rules">{payload.rules}</div>
            )}
          </div>
        </div>
      )

    case 'PillarsClosing':
      return (
        <div className="wn-slide wn-slide-pillars" style={{ background: primaryColor }}>
          <h1>Our 3 Pillars</h1>
          <div className="wn-pillars-grid">
            {(payload?.pillars || [
              { name: 'Clinical', description: 'Excellence in care' },
              { name: 'Cultural', description: 'Our people, our values' },
              { name: 'Financial', description: 'Sustainable success' }
            ]).map((pillar, idx) => (
              <div key={idx} className="wn-pillar">
                <h3 style={{ color: primaryColor }}>{pillar.name}</h3>
                <p>{pillar.description}</p>
              </div>
            ))}
          </div>
        </div>
      )

    default:
      return (
        <div className="wn-slide wn-slide-content">
          <div className="wn-slide-header" style={{ background: primaryColor }}>
            <h1>{slide_type}</h1>
          </div>
          <div className="wn-slide-body">
            <pre style={{ fontSize: 14, color: '#6b7280' }}>
              {JSON.stringify(payload, null, 2)}
            </pre>
          </div>
        </div>
      )
  }
}

export default WelcomeNightsPresent
