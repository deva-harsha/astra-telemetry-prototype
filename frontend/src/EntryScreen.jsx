import { ArrowDownRight, ArrowRight, Radio } from 'lucide-react'

export default function EntryScreen({ phase, serviceMessage, serviceStatus, onEnter, onExplore, headingRef }) {
  return <section className={`entry-screen entry-${phase}`} aria-label="ASTRA entry screen" aria-hidden={phase === 'leaving'} inert={phase === 'leaving'}>
    <div className="entry-atmosphere" aria-hidden="true"><div className="entry-stars" /><div className="entry-orbit entry-orbit-one" /><div className="entry-orbit entry-orbit-two" /><div className="entry-orbit-light" /></div>
    <div className="entry-inner">
      <header className="entry-header"><div className="entry-brand"><span className="entry-mark" aria-hidden="true">✦</span><strong>ASTRA</strong><span>Spacecraft Telemetry Decision Support</span></div><span className="entry-header-tag">PROTOTYPE / GROUND SEGMENT</span></header>
      <div className="entry-main"><div className="entry-copy"><p className="entry-eyebrow"><span className="entry-eyebrow-line" />GROUND-BASED MISSION INTELLIGENCE</p><h1 ref={headingRef} tabIndex={-1}>See the signal.<br /><em>Understand the event.</em></h1><p className="entry-description">ASTRA transforms spacecraft telemetry into persistent anomaly events, supporting evidence and clear operator-review workflows.</p><div className="entry-actions"><button type="button" className="entry-primary" onClick={onEnter}>ENTER MISSION CONTROL <ArrowRight size={19} aria-hidden="true" /></button><button type="button" className="entry-secondary" onClick={onExplore}>EXPLORE CAPABILITIES <ArrowDownRight size={18} aria-hidden="true" /></button></div></div><div className="entry-side" aria-hidden="true"><span>ASTRA / SYSTEM OVERVIEW</span><div className="entry-side-orbit"><span>01</span><i /></div><p>GROUND SYSTEM<br />TELEMETRY ANALYSIS<br />OPERATOR REVIEW</p></div></div>
      <div className="entry-boundaries" aria-label="Prototype boundaries"><span>Simulated and recorded telemetry</span><span>Hybrid anomaly detection</span><span>Human review required</span><span>No spacecraft command access</span></div>
      <footer className="entry-footer"><div className={`entry-service service-${serviceStatus}`} role="status" aria-live="polite"><Radio size={15} aria-hidden="true" />{serviceMessage}</div><div>MISSION: ASTRA-01</div><div>PROTOTYPE ENVIRONMENT</div></footer>
    </div>
  </section>
}
