import React, { useState } from "react";
import { ChevronRight } from "lucide-react";
import "./CollapsibleSection.css";

/**
 * @param {{ icon?: string, title: string, defaultOpen?: boolean, children: React.ReactNode }} props
 */
export default function CollapsibleSection({ icon, title, defaultOpen = true, children }) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className="collapsible-section">
      <button className="collapsible-section__header" onClick={() => setOpen((o) => !o)}>
        <ChevronRight
          size={15}
          strokeWidth={2}
          className="collapsible-section__chevron"
          style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)" }}
        />
        {icon && <span className="collapsible-section__icon">{icon}</span>}
        <span className="collapsible-section__title">{title}</span>
      </button>
      {open && <div className="collapsible-section__body">{children}</div>}
    </div>
  );
}
