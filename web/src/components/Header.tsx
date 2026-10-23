import React from "react";

export const Header: React.FC = () => {
  return (
    <header className="app-header">
      <div className="logo-badge">
        <div className="logo-icon">AM</div>
        <div>
          <span className="logo-title">ASCII-MOTION</span>
          <span className="logo-tagline">STUDIO v0.1.0</span>
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
        <a
          href="https://github.com/rajveersinh-is-dev/ascii-motion"
          target="_blank"
          rel="noreferrer"
          className="btn btn-sm"
          style={{ textDecoration: "none" }}
        >
          GitHub Repo
        </a>
      </div>
    </header>
  );
};
