import React, { useState, useRef, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { Globe, ChevronDown, Check } from "lucide-react";

export const LanguageSwitcher: React.FC = () => {
  const { i18n, t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentLang = (i18n.language || "en").substring(0, 2);

  const languages = [
    { code: "en", label: "EN", fullLabel: "EN — English" },
    { code: "fr", label: "FR", fullLabel: "FR — Français" },
  ];

  const handleSelectLanguage = (code: string) => {
    i18n.changeLanguage(code);
    setIsOpen(false);
  };

  // Close when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      setIsOpen(false);
    } else if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
      if (!isOpen) {
        e.preventDefault();
        setIsOpen(true);
      }
    }
  };

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        type="button"
        id="language-selector-button"
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={t("nav.selectLanguage", "Select language")}
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        className="flex items-center gap-2 rounded-lg bg-secondary/60 px-2.5 py-1.5 text-xs font-semibold text-foreground hover:bg-secondary hover:text-white transition-colors border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
      >
        <Globe className="h-3.5 w-3.5 text-blue-400 shrink-0" aria-hidden="true" />
        <span className="tracking-wide">{currentLang === "fr" ? "FR — Français" : "EN — English"}</span>
        <ChevronDown className="h-3 w-3 text-muted-foreground transition-transform" aria-hidden="true" />
      </button>

      {isOpen && (
        <ul
          role="listbox"
          aria-labelledby="language-selector-button"
          tabIndex={-1}
          className="absolute right-0 z-50 mt-1.5 w-40 origin-top-right rounded-xl border border-border bg-slate-900/95 p-1 shadow-xl backdrop-blur-md focus:outline-none animate-in fade-in zoom-in-95 duration-100"
        >
          {languages.map((lang) => {
            const isSelected = currentLang === lang.code;
            return (
              <li
                key={lang.code}
                role="option"
                aria-selected={isSelected}
                tabIndex={0}
                onClick={() => handleSelectLanguage(lang.code)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    handleSelectLanguage(lang.code);
                  }
                }}
                className={`flex items-center justify-between rounded-lg px-3 py-2 text-xs font-medium cursor-pointer transition-colors focus:bg-primary/20 focus:text-white focus:outline-none ${
                  isSelected
                    ? "bg-primary text-white shadow-sm"
                    : "text-slate-300 hover:bg-secondary/70 hover:text-white"
                }`}
              >
                <span>{lang.fullLabel}</span>
                {isSelected && <Check className="h-3.5 w-3.5 text-white" aria-hidden="true" />}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
};
