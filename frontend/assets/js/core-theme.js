(function () {
  'use strict';

  const storageKey = 'mininode-theme';
  const media = window.matchMedia('(prefers-color-scheme: dark)');

  function savedTheme() {
    try {
      const value = window.localStorage.getItem(storageKey);
      return value === 'light' || value === 'dark' ? value : null;
    } catch (_error) {
      return null;
    }
  }

  function currentTheme() {
    return document.documentElement.dataset.theme || (media.matches ? 'dark' : 'light');
  }

  function updateControls() {
    const isDark = currentTheme() === 'dark';
    document.querySelectorAll('[data-theme-toggle]').forEach((control) => {
      const nextTheme = isDark ? 'claro' : 'oscuro';
      control.setAttribute('aria-label', `Cambiar a tema ${nextTheme}`);
      control.setAttribute('title', `Cambiar a tema ${nextTheme}`);
      control.setAttribute('aria-pressed', String(isDark));
      const label = control.querySelector('[data-theme-label]');
      if (label) label.textContent = isDark ? 'Claro' : 'Oscuro';
    });
  }

  function selectTheme(theme) {
    document.documentElement.dataset.theme = theme;
    try {
      window.localStorage.setItem(storageKey, theme);
    } catch (_error) {
      // The selected theme still applies when storage is unavailable.
    }
    updateControls();
  }

  const preference = savedTheme();
  if (preference) document.documentElement.dataset.theme = preference;

  document.addEventListener('DOMContentLoaded', () => {
    updateControls();
    document.querySelectorAll('[data-theme-toggle]').forEach((control) => {
      control.addEventListener('click', () => {
        selectTheme(currentTheme() === 'dark' ? 'light' : 'dark');
      });
    });
  });

  media.addEventListener?.('change', () => {
    if (!savedTheme()) updateControls();
  });
}());
