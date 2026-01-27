import React, { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Check, Play, Download, FileText } from 'lucide-react'
import {
  getWNBrands,
  getWNFacilities,
  getWNAgendaTemplates,
  getWNGames,
  getWNPresentation,
  createWNPresentation,
  updateWNPresentation,
  buildWNSlides,
  getWNExportPptxUrl,
  getWNExportPdfUrl
} from '../services/api'

const STEPS = [
  { id: 1, label: 'Brand & Facility' },
  { id: 2, label: 'Template' },
  { id: 3, label: 'Configure' },
  { id: 4, label: 'Preview' }
]

const SLIDE_TYPE_NAMES = {
  'WelcomeIntro': 'Welcome & Introduction',
  'RaffleBumper': 'Raffle',
  'HistoryBlock': 'Our History',
  'FootprintBlock': 'Our Footprint',
  'RegionsBlock': 'Our Regions',
  'CultureBlock': 'Culture & Values',
  'GameSlide': 'Game / Activity',
  'PillarsClosing': '3 Pillars Closing'
}

function WelcomeNightsWizard() {
  const navigate = useNavigate()
  const { id } = useParams()
  const isEditing = !!id

  const [step, setStep] = useState(1)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  // Data
  const [brands, setBrands] = useState([])
  const [facilities, setFacilities] = useState([])
  const [templates, setTemplates] = useState([])
  const [games, setGames] = useState([])

  // Form state
  const [selectedBrandId, setSelectedBrandId] = useState(null)
  const [selectedFacilityId, setSelectedFacilityId] = useState(null)
  const [selectedTemplateId, setSelectedTemplateId] = useState(null)
  const [title, setTitle] = useState('')
  const [config, setConfig] = useState({
    raffle_count: 3,
    selected_game_ids: [],
    include_history: true,
    include_footprint: true,
    include_regions: true,
    include_culture: true
  })
  const [previewSlides, setPreviewSlides] = useState([])
  const [presentationId, setPresentationId] = useState(null)

  useEffect(() => {
    loadData()
  }, [])

  useEffect(() => {
    if (selectedBrandId) {
      loadTemplatesAndGames()
    }
  }, [selectedBrandId])

  const loadData = async () => {
    setLoading(true)
    try {
      const [brandsData, facilitiesData] = await Promise.all([
        getWNBrands(),
        getWNFacilities()
      ])
      setBrands(brandsData)
      setFacilities(facilitiesData)

      // If editing, load existing presentation
      if (id) {
        const presentation = await getWNPresentation(id)
        setPresentationId(presentation.id)
        setSelectedBrandId(presentation.brand_id)
        setSelectedFacilityId(presentation.facility_id)
        setSelectedTemplateId(presentation.agenda_template_id)
        setTitle(presentation.title)
        if (presentation.config) {
          setConfig({ ...config, ...presentation.config })
        }
        if (presentation.slide_instances && presentation.slide_instances.length > 0) {
          setPreviewSlides(presentation.slide_instances.map(s => ({
            slide_type: s.slide_type,
            payload: s.payload
          })))
        }
      }
    } catch (err) {
      console.error('Error loading data:', err)
    } finally {
      setLoading(false)
    }
  }

  const loadTemplatesAndGames = async () => {
    try {
      const [templatesData, gamesData] = await Promise.all([
        getWNAgendaTemplates({ brand_id: selectedBrandId }),
        getWNGames({ brand_id: selectedBrandId })
      ])
      setTemplates(templatesData)
      setGames(gamesData)

      // If no template selected yet, select the first one
      if (!selectedTemplateId && templatesData.length > 0) {
        setSelectedTemplateId(templatesData[0].id)
        if (templatesData[0].default_config) {
          setConfig({ ...config, ...templatesData[0].default_config })
        }
      }

      // Auto-select ice breaker and some challenge games if none selected
      if (config.selected_game_ids.length === 0 && gamesData.length > 0) {
        const icebreaker = gamesData.find(g => g.game_type === 'icebreaker')
        const challenges = gamesData.filter(g => g.game_type === 'challenge').slice(0, 3)
        const defaultIds = [...(icebreaker ? [icebreaker.id] : []), ...challenges.map(g => g.id)]
        setConfig({ ...config, selected_game_ids: defaultIds })
      }
    } catch (err) {
      console.error('Error loading templates/games:', err)
    }
  }

  const handleBrandSelect = (brandId) => {
    setSelectedBrandId(brandId)
    setSelectedFacilityId(null)
    setSelectedTemplateId(null)
    setConfig({ ...config, selected_game_ids: [] })
  }

  const handleTemplateSelect = (templateId) => {
    setSelectedTemplateId(templateId)
    const template = templates.find(t => t.id === templateId)
    if (template && template.default_config) {
      setConfig({ ...config, ...template.default_config })
    }
  }

  const handleGameToggle = (gameId) => {
    const newIds = config.selected_game_ids.includes(gameId)
      ? config.selected_game_ids.filter(id => id !== gameId)
      : [...config.selected_game_ids, gameId]
    setConfig({ ...config, selected_game_ids: newIds })
  }

  const generateTitle = () => {
    const facility = facilities.find(f => f.id === selectedFacilityId)
    const template = templates.find(t => t.id === selectedTemplateId)
    if (facility && template) {
      const date = new Date().toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
      return `${facility.name} - ${template.name} - ${date}`
    }
    return ''
  }

  const canProceed = () => {
    switch (step) {
      case 1: return selectedBrandId && selectedFacilityId
      case 2: return selectedTemplateId
      case 3: return true
      case 4: return title.trim().length > 0
      default: return false
    }
  }

  const handleNext = async () => {
    if (step === 3) {
      // Generate title if empty
      if (!title) {
        setTitle(generateTitle())
      }
      // Build preview
      await buildPreview()
    }
    if (step < 4) {
      setStep(step + 1)
    }
  }

  const buildPreview = async () => {
    // Create or update presentation first
    try {
      setSaving(true)
      let presId = presentationId

      if (!presId) {
        // Create new presentation
        const data = {
          brand_id: selectedBrandId,
          facility_id: selectedFacilityId,
          agenda_template_id: selectedTemplateId,
          title: title || generateTitle(),
          config: config,
          created_by: 'Tim Nelson'
        }
        const newPres = await createWNPresentation(data)
        presId = newPres.id
        setPresentationId(presId)
      } else {
        // Update existing
        await updateWNPresentation(presId, {
          title: title || generateTitle(),
          config: config
        })
      }

      // Build slides
      const result = await buildWNSlides(presId, config)
      // Reload presentation to get slides
      const presentation = await getWNPresentation(presId)
      if (presentation.slide_instances) {
        setPreviewSlides(presentation.slide_instances)
      }
    } catch (err) {
      console.error('Error building preview:', err)
    } finally {
      setSaving(false)
    }
  }

  const handleCreate = async () => {
    setSaving(true)
    try {
      if (presentationId) {
        await updateWNPresentation(presentationId, {
          title: title,
          config: config,
          status: 'ready'
        })
        await buildWNSlides(presentationId, config)
      }
      navigate('/welcome-nights')
    } catch (err) {
      console.error('Error saving presentation:', err)
    } finally {
      setSaving(false)
    }
  }

  const filteredFacilities = facilities.filter(f => f.brand_id === selectedBrandId)
  const icebreakers = games.filter(g => g.game_type === 'icebreaker')
  const challenges = games.filter(g => g.game_type === 'challenge')

  if (loading) {
    return (
      <div className="empty-state">
        <div className="animate-spin" style={{ width: 40, height: 40, border: '3px solid #e5e7eb', borderTopColor: '#0b7280', borderRadius: '50%', margin: '0 auto 16px' }} />
        <p>Loading...</p>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">{isEditing ? 'Edit Presentation' : 'New Presentation'}</h1>
          <p className="page-subtitle">Create a Welcome Night or Culture Night presentation</p>
        </div>
      </div>

      <div className="wn-wizard">
        {/* Steps indicator */}
        <div className="wn-wizard-steps">
          {STEPS.map((s, idx) => (
            <div
              key={s.id}
              className={`wn-wizard-step ${step === s.id ? 'active' : ''} ${step > s.id ? 'completed' : ''}`}
            >
              <div className="wn-wizard-step-number">
                {step > s.id ? <Check size={16} /> : s.id}
              </div>
              <div className="wn-wizard-step-label">{s.label}</div>
            </div>
          ))}
        </div>

        {/* Step content */}
        <div className="wn-wizard-content">
          {/* Step 1: Brand & Facility */}
          {step === 1 && (
            <div>
              <h3 className="card-title mb-4">Select Brand</h3>
              <div className="wn-brand-options">
                {brands.map(brand => (
                  <div
                    key={brand.id}
                    className={`wn-brand-option ${selectedBrandId === brand.id ? 'selected' : ''}`}
                    onClick={() => handleBrandSelect(brand.id)}
                    style={{ borderColor: selectedBrandId === brand.id ? brand.primary_color : undefined }}
                  >
                    <div className="wn-brand-option-name" style={{ color: brand.primary_color }}>
                      {brand.name}
                    </div>
                    <div className="wn-brand-option-desc">{brand.slug}</div>
                  </div>
                ))}
              </div>

              {selectedBrandId && (
                <>
                  <h3 className="card-title mb-4 mt-6">Select Facility</h3>
                  {filteredFacilities.length === 0 ? (
                    <p className="text-muted">No facilities found for this brand. Add facilities in admin.</p>
                  ) : (
                    <div className="wn-facility-list">
                      {filteredFacilities.map(facility => (
                        <div
                          key={facility.id}
                          className={`wn-facility-option ${selectedFacilityId === facility.id ? 'selected' : ''}`}
                          onClick={() => setSelectedFacilityId(facility.id)}
                        >
                          <div style={{ fontWeight: 600 }}>{facility.name}</div>
                          <div style={{ fontSize: 13, color: '#6b7280' }}>
                            {facility.city}, {facility.state}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* Step 2: Template */}
          {step === 2 && (
            <div>
              <h3 className="card-title mb-4">Select Agenda Template</h3>
              <div className="wn-facility-list">
                {templates.map(template => (
                  <div
                    key={template.id}
                    className={`wn-facility-option ${selectedTemplateId === template.id ? 'selected' : ''}`}
                    onClick={() => handleTemplateSelect(template.id)}
                  >
                    <div style={{ fontWeight: 600 }}>{template.name}</div>
                    <div style={{ fontSize: 13, color: '#6b7280' }}>{template.description}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Step 3: Configure */}
          {step === 3 && (
            <div>
              <div className="wn-config-section">
                <h3 className="wn-config-section-title">Content Blocks</h3>
                <div className="wn-toggle-list">
                  <label className="wn-toggle-item">
                    <input
                      type="checkbox"
                      checked={config.include_history}
                      onChange={(e) => setConfig({ ...config, include_history: e.target.checked })}
                    />
                    <span>Include History Timeline</span>
                  </label>
                  <label className="wn-toggle-item">
                    <input
                      type="checkbox"
                      checked={config.include_footprint}
                      onChange={(e) => setConfig({ ...config, include_footprint: e.target.checked })}
                    />
                    <span>Include Our Footprint</span>
                  </label>
                  <label className="wn-toggle-item">
                    <input
                      type="checkbox"
                      checked={config.include_regions}
                      onChange={(e) => setConfig({ ...config, include_regions: e.target.checked })}
                    />
                    <span>Include Regions Map</span>
                  </label>
                  <label className="wn-toggle-item">
                    <input
                      type="checkbox"
                      checked={config.include_culture}
                      onChange={(e) => setConfig({ ...config, include_culture: e.target.checked })}
                    />
                    <span>Include Culture Block</span>
                  </label>
                </div>
              </div>

              <div className="wn-config-section">
                <h3 className="wn-config-section-title">Raffle Slides</h3>
                <div className="wn-number-input">
                  <label>Number of raffle slides:</label>
                  <input
                    type="number"
                    className="form-input"
                    min={0}
                    max={10}
                    value={config.raffle_count}
                    onChange={(e) => setConfig({ ...config, raffle_count: parseInt(e.target.value) || 0 })}
                  />
                </div>
              </div>

              <div className="wn-config-section">
                <h3 className="wn-config-section-title">Games</h3>
                {icebreakers.length > 0 && (
                  <>
                    <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 8 }}>Ice Breaker</p>
                    <div className="wn-game-list mb-4">
                      {icebreakers.map(game => (
                        <label key={game.id} className={`wn-game-item ${config.selected_game_ids.includes(game.id) ? 'selected' : ''}`}>
                          <input
                            type="checkbox"
                            checked={config.selected_game_ids.includes(game.id)}
                            onChange={() => handleGameToggle(game.id)}
                          />
                          <div className="wn-game-info">
                            <div className="wn-game-title">{game.title}</div>
                            <div className="wn-game-meta">
                              {game.duration_minutes && `${game.duration_minutes} min`}
                              {game.value_label && ` | ${game.value_label}`}
                            </div>
                          </div>
                          <span className="wn-game-type-badge icebreaker">Ice Breaker</span>
                        </label>
                      ))}
                    </div>
                  </>
                )}
                {challenges.length > 0 && (
                  <>
                    <p style={{ fontSize: 12, color: '#6b7280', marginBottom: 8 }}>Challenge Games (Minute-to-Win-It)</p>
                    <div className="wn-game-list">
                      {challenges.map(game => (
                        <label key={game.id} className={`wn-game-item ${config.selected_game_ids.includes(game.id) ? 'selected' : ''}`}>
                          <input
                            type="checkbox"
                            checked={config.selected_game_ids.includes(game.id)}
                            onChange={() => handleGameToggle(game.id)}
                          />
                          <div className="wn-game-info">
                            <div className="wn-game-title">{game.title}</div>
                            <div className="wn-game-meta">
                              {game.duration_minutes && `${game.duration_minutes} min`}
                              {game.value_label && ` | ${game.value_label}`}
                            </div>
                          </div>
                          <span className="wn-game-type-badge challenge">Challenge</span>
                        </label>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Step 4: Preview */}
          {step === 4 && (
            <div>
              <div className="form-group">
                <label className="form-label">Presentation Title</label>
                <input
                  type="text"
                  className="form-input"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Enter a title for this presentation"
                />
              </div>

              <h3 className="wn-config-section-title mt-6">Slide Outline ({previewSlides.length} slides)</h3>
              {previewSlides.length === 0 ? (
                <p className="text-muted">Building preview...</p>
              ) : (
                <ul className="wn-preview-outline">
                  {previewSlides.map((slide, idx) => (
                    <li key={idx} className="wn-preview-slide">
                      <div className="wn-preview-slide-number">{idx + 1}</div>
                      <div className={`wn-preview-slide-type ${slide.slide_type === 'RaffleBumper' ? 'raffle' : ''}`}>
                        {SLIDE_TYPE_NAMES[slide.slide_type] || slide.slide_type}
                        {slide.payload?.title && slide.slide_type === 'GameSlide' && (
                          <span style={{ color: '#6b7280', fontWeight: 400 }}> - {slide.payload.title}</span>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}

              {presentationId && (
                <div className="wn-export-buttons mt-6">
                  <button
                    className="btn btn-secondary"
                    onClick={() => navigate(`/welcome-nights/${presentationId}/present`)}
                  >
                    <Play size={16} />
                    <span>Preview</span>
                  </button>
                  <a className="btn btn-secondary" href={getWNExportPptxUrl(presentationId)}>
                    <Download size={16} />
                    <span>Download PPTX</span>
                  </a>
                  <a className="btn btn-secondary" href={getWNExportPdfUrl(presentationId)}>
                    <FileText size={16} />
                    <span>Download PDF</span>
                  </a>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="wn-wizard-actions">
          <button
            className="btn btn-secondary"
            onClick={() => step > 1 ? setStep(step - 1) : navigate('/welcome-nights')}
          >
            <ChevronLeft size={18} />
            <span>{step > 1 ? 'Back' : 'Cancel'}</span>
          </button>

          {step < 4 ? (
            <button
              className="btn btn-primary"
              onClick={handleNext}
              disabled={!canProceed() || saving}
            >
              <span>{saving ? 'Building...' : 'Next'}</span>
              <ChevronRight size={18} />
            </button>
          ) : (
            <button
              className="btn btn-primary"
              onClick={handleCreate}
              disabled={!canProceed() || saving}
            >
              <Check size={18} />
              <span>{saving ? 'Saving...' : (isEditing ? 'Save Changes' : 'Create Presentation')}</span>
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default WelcomeNightsWizard
