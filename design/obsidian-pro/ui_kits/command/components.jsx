/* global React */
const { useState, useEffect } = React;

// Lucide icon wrapper — the global `lucide` object exposes createIcons()
// after the script loads. We render an <i> with the data attribute and
// trigger a re-scan after every render. Cheap and correct for this kit.
function Icon({ name, size = 16, className = "", style = {} }) {
  useEffect(() => {
    if (window.lucide) window.lucide.createIcons();
  });
  return (
    <i
      data-lucide={name}
      className={className}
      style={{ width: size, height: size, display: "inline-flex", ...style }}
    />
  );
}

function Button({ variant = "secondary", size = "md", icon, children, onClick, disabled }) {
  const cls = `ds-btn ds-btn--${variant}` + (size !== "md" ? ` ds-btn--${size}` : "");
  return (
    <button className={cls} onClick={onClick} disabled={disabled}>
      {icon && <Icon name={icon} size={14} />}
      {children}
    </button>
  );
}

function Badge({ tone = "medium", dot = false, children }) {
  return (
    <span className={`ds-badge ds-badge--${tone}`}>
      {dot && <span className="ds-badge__dot" />}
      {children}
    </span>
  );
}

function Stat({ label, value, unit, delta, deltaTone = "muted", critical }) {
  return (
    <div className={"ds-stat" + (critical ? " ds-stat--critical" : "")}>
      <p className="ds-stat__label">{label}</p>
      <p className="ds-stat__value" style={critical ? {} : { color: "var(--ds-text)" }}>
        {value}
        {unit && <span style={{ fontSize: 14, fontWeight: 400, marginLeft: 2 }}>{unit}</span>}
      </p>
      {delta && (
        <p
          className="ds-stat__delta"
          style={{ color: critical ? "currentColor" : `var(--ds-${deltaTone === "muted" ? "text-muted" : deltaTone})` }}
        >
          {delta}
        </p>
      )}
    </div>
  );
}

function Field({ label, helper, error, children }) {
  return (
    <div className="ds-field">
      {label && <label className="ds-label">{label}</label>}
      {children}
      {error ? (
        <span className="ds-error-text">{error}</span>
      ) : helper ? (
        <span className="ds-helper">{helper}</span>
      ) : null}
    </div>
  );
}

function Input({ error, ...rest }) {
  return <input className={"ds-input" + (error ? " ds-input--error" : "")} {...rest} />;
}

function Select({ children, ...rest }) {
  return <select className="ds-select" {...rest}>{children}</select>;
}

function Search({ value, onChange, placeholder = "Search…" }) {
  return (
    <div className="ds-search" style={{ position: "relative" }}>
      <Icon
        name="search"
        size={14}
        style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--ds-text-faint)", pointerEvents: "none" }}
      />
      <input
        className="ds-input"
        style={{ paddingLeft: 32 }}
        type="text"
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}

function Checkbox({ checked, onChange, children }) {
  return (
    <label className="ds-checkbox">
      <input type="checkbox" checked={checked} onChange={(e) => onChange?.(e.target.checked)} />
      {children}
    </label>
  );
}

function Header({ theme, onToggleTheme }) {
  return (
    <header className="app-header">
      <div className="header-left">
        <div className="header-logo">C</div>
        <span className="header-title">Command</span>
        <span className="header-version">v1.2</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <span className="header-palette">Obsidian Pro</span>
        <button
          className="ds-btn ds-btn--ghost ds-btn--sm"
          onClick={onToggleTheme}
          title="Toggle theme"
          style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
        >
          <Icon name={theme === "dark" ? "sun" : "moon"} size={14} />
          {theme === "dark" ? "Light" : "Dark"}
        </button>
      </div>
    </header>
  );
}

const NAV = [
  { id: "dashboard",  icon: "layout-dashboard", label: "Dashboard" },
  { id: "detections", icon: "alert-triangle",   label: "Detections" },
  { id: "assets",     icon: "database",         label: "Assets" },
  { id: "policies",   icon: "clipboard-list",   label: "Policies" },
  { id: "logs",       icon: "list",             label: "Logs" },
];

function NavRail({ screen, onScreen }) {
  return (
    <nav className="ds-nav" style={{ position: "sticky", top: 52, height: "calc(100vh - 52px)" }}>
      <div className="ds-nav__logo">C</div>
      {NAV.map((n) => (
        <div
          key={n.id}
          className={"ds-nav__item" + (screen === n.id ? " active" : "")}
          onClick={() => onScreen(n.id)}
          title={n.label}
        >
          <Icon name={n.icon} size={16} />
        </div>
      ))}
      <div className="ds-nav__spacer" />
      <div className="ds-nav__item" title="Settings">
        <Icon name="settings" size={16} />
      </div>
    </nav>
  );
}

Object.assign(window, {
  Icon, Button, Badge, Stat, Field, Input, Select, Search, Checkbox, Header, NavRail, NAV,
});
