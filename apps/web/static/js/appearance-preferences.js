/* Live examples stay inside the preview; the regular POST saves validated preferences. */
(function (root) {
  "use strict";
  const modes = { forest: "dark", paper: "light", dark: "dark", midnight: "dark" };
  function accentTextColor(color) {
    const channels = [1, 3, 5].map(index => parseInt(color.slice(index, index + 2), 16) / 255);
    const linear = channels.map(value => value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4);
    const luminance = linear.reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
    return luminance > 0.179 ? "#000000" : "#ffffff";
  }
  function configuration(fields, useThemeAccent) {
    return {
      palette: fields.theme.value, mode: modes[fields.theme.value], font: fields.font.value,
      density: fields.density.value, accent: useThemeAccent ? null : fields.accent.value,
      radius: Number(fields.radius.value),
    };
  }
  function applyPreview(preview, value) {
    preview.dataset.previewPalette = value.palette;
    preview.dataset.previewMode = value.mode;
    preview.dataset.font = value.font;
    preview.dataset.density = value.density;
    preview.style.setProperty("--radius-md", `${value.radius}px`);
    for (const token of ["--color-primary", "--color-on-primary"]) preview.style.removeProperty(token);
    if (value.accent) {
      preview.style.setProperty("--color-primary", value.accent);
      preview.style.setProperty("--color-on-primary", accentTextColor(value.accent));
    }
  }
  async function copyConfiguration(value, clipboard, fallback, status) {
    const text = JSON.stringify(value, null, 2);
    try {
      if (!clipboard?.writeText) throw new Error("Clipboard unavailable");
      await clipboard.writeText(text);
      status.textContent = "Configuration copied.";
    } catch {
      fallback.parentElement.hidden = false;
      fallback.value = text;
      fallback.focus();
      fallback.select();
      status.textContent = "Select and copy the configuration below.";
    }
  }
  function initialize(document) {
    const form = document.querySelector("[data-appearance-form]");
    if (!form) return;
    const preview = document.querySelector("[data-appearance-preview]");
    const fields = Object.fromEntries(["theme", "font", "density", "accent", "radius"].map(
      key => [key, form.querySelector(`[name="${key}"]`)]));
    const defaultInput = form.querySelector("[data-accent-default]");
    const status = document.querySelector("[data-appearance-status]");
    const fallback = document.querySelector("[data-configuration-text]");
    const swatches = Array.from(form.querySelectorAll?.("[data-accent-swatch]") || []);
    let useThemeAccent = fields.accent.dataset.defaultAccent === "true";
    const update = () => {
      defaultInput.disabled = !useThemeAccent;
      fields.accent.name = useThemeAccent ? "" : "accent";
      const value = configuration(fields, useThemeAccent);
      applyPreview(preview, value);
      if (useThemeAccent) {
        const color = root.getComputedStyle(preview).getPropertyValue("--color-primary").trim();
        if (/^#[0-9a-f]{6}$/i.test(color)) fields.accent.value = color;
      }
      document.querySelector("[data-radius-output]").value = value.radius;
      swatches.forEach(swatch => swatch.setAttribute("aria-pressed", String(
        swatch.dataset.accentSwatch.toLowerCase() === fields.accent.value.toLowerCase())));
      fallback.parentElement.hidden = true;
      status.textContent = "";
    };
    form.addEventListener("input", event => {
      if (event.target === fields.accent) useThemeAccent = false;
      update();
    });
    form.addEventListener("change", event => {
      if (event.target === fields.accent) useThemeAccent = false;
      update();
    });
    const reset = form.querySelector("[data-accent-reset]");
    swatches.forEach(swatch => {
      swatch.hidden = false;
      swatch.addEventListener("click", () => {
        fields.accent.value = swatch.dataset.accentSwatch;
        useThemeAccent = false;
        update();
      });
    });
    reset.hidden = false;
    reset.addEventListener("click", () => { useThemeAccent = true; update(); });
    const copy = document.querySelector("[data-copy-appearance]");
    copy.hidden = false;
    copy.addEventListener("click", () => copyConfiguration(
      configuration(fields, useThemeAccent), root.navigator?.clipboard, fallback, status));
    const title = preview.querySelector("[data-preview-title]");
    const body = preview.querySelector("[data-preview-body]");
    const edit = preview.querySelector("[data-preview-edit]");
    const newNote = preview.querySelector("[data-preview-new]");
    const startEditing = () => {
      title.contentEditable = "true";
      body.contentEditable = "true";
      title.focus();
      status.textContent = "Editing the preview. Your published notes are unchanged.";
    };
    edit.hidden = false;
    newNote.hidden = false;
    edit.addEventListener("click", startEditing);
    newNote.addEventListener("click", () => {
      title.textContent = "Untitled note";
      body.textContent = "Write your next idea here.";
      startEditing();
    });
    update();
  }
  if (typeof module !== "undefined") module.exports = { accentTextColor, configuration, applyPreview, copyConfiguration, initialize };
  if (root.document) initialize(root.document);
})(typeof window === "undefined" ? globalThis : window);
